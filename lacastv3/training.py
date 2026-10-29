"""Resumable documentation -> candidate -> execution -> refinement workflow."""
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

import httpx
from openai import OpenAI, APIError

from .compiler import compile_rules, SQL_TOKENS
from .coverage import target_samples
from .database import MySQLDatabase
from .generator import SQLGenerator
from .parser import SQLParser
from .productions import Rule

ROOT = Path(__file__).resolve().parents[1]


def save(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


@contextmanager
def exclusive_run(directory):
    directory.mkdir(parents=True, exist_ok=True)
    stream = (directory / '.lock').open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            stream.seek(0)
            if not stream.read(1):
                stream.write(b'0')
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        stream.close()


class Trainer:
    def __init__(self, directory: Path, database: MySQLDatabase, feature_limit=0):
        self.directory = directory
        self.db = database
        self.feature_limit = feature_limit
        self.constants = json.loads((ROOT / 'configs/mysql/semantics.json').read_text())['types']
        self.schema = json.loads((ROOT / 'configs/mysql/schema.json').read_text())
        self.corpus = json.loads((ROOT / 'configs/mysql/web_corpus.json').read_text(encoding='utf-8'))
        self.events = directory / 'events.jsonl'
        self.state_path = directory / 'training_state.json'
        self.rules_path = directory / 'trained_rules.json'
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {
            'completed_features': [], 'failed_features': [], 'llm_calls': 0, 'status': 'running',
            'created_at': datetime.now(timezone.utc).isoformat(), 'elapsed_seconds': 0,
        }
        self.accepted = [Rule(**data) for data in json.loads(self.rules_path.read_text())] if self.rules_path.exists() else []
        self.client = None

    def event(self, kind, **data):
        with self.events.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                                     'event': kind, **data}, ensure_ascii=False) + '\n')

    def propose(self, feature, description, feedback=None):
        if self.client is None:
            self.client = OpenAI(api_key=os.environ['LLM_API_KEY'],
                base_url=os.getenv('LLM_BASE_URL'), timeout=180, max_retries=2,
                http_client=httpx.Client(verify=os.getenv('LLM_VERIFY_SSL', 'true').lower() != 'false'))
        self.state['llm_calls'] += 1
        self.event('llm_call', feature=feature, feedback=feedback is not None)
        request = {'feature': feature, 'documentation': description,
                   'supported_types': list(self.constants), 'feedback': feedback}
        response = self.client.chat.completions.create(
            model=os.environ['LLM_MODEL'], temperature=0,
            messages=[{'role': 'system', 'content': (ROOT / 'prompts/rules.txt').read_text()},
                      {'role': 'user', 'content': json.dumps(request, ensure_ascii=False)}],
            response_format={'type': 'json_object'},
        )
        if response.choices[0].finish_reason == 'length':
            raise ValueError('LLM output truncated; no partial rules are accepted')
        content = response.choices[0].message.content
        content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content.strip())
        data = json.loads(content)
        result = []
        for candidate in data['rules']:
            dtype = candidate['return_type']
            production = candidate['production']
            aggregate = candidate.get('aggregate', False)
            if dtype not in self.constants or not isinstance(aggregate, bool):
                raise ValueError('Invalid return type or aggregate flag')
            # Stable content IDs permit shared documented aliases without duplicate parser rules.
            identity = hashlib.sha256(json.dumps([dtype, production, aggregate]).encode()).hexdigest()[:24]
            rule = Rule(identity, dtype, production, aggregate)
            rule.tree
            function = re.match(r'\s*([A-Za-z_][A-Za-z_0-9]*)\s*\(', feature)
            if function:
                words = set()
                def collect(node):
                    if node.kind == 'literal':
                        words.update(token.upper() for token in SQL_TOKENS.findall(node.value))
                    for child in node.children:
                        collect(child)
                collect(rule.tree)
                if function[1].upper() not in words:
                    raise ValueError(f'Candidate removed the requested function {function[1]}')
            if rule not in result:
                result.append(rule)
        if not result:
            raise ValueError('LLM returned no rules')
        return result

    def evaluate(self, rule, directory, seed):
        directory.mkdir(parents=True, exist_ok=False)
        all_rules = [rule] + [other for other in self.accepted if other.id != rule.id]
        grammar = directory / 'LearnedMySQL.g4'
        mapping = compile_rules(ROOT / 'configs/mysql/MySQLBase.g4', all_rules, grammar)
        syntax = SQLParser(grammar, ROOT / 'vendor/antlr-4.13.2-complete.jar',
                           self.directory / 'parser_cache', mapping)
        generator = SQLGenerator(self.schema, self.constants, all_rules, seed=seed)
        conn = self.db.connect()
        batches = []
        try:
            with (directory / 'sql_results.jsonl').open('w', encoding='utf-8') as stream:
                for batch in range(3):
                    retained = []
                    generated = discarded = 0
                    while len(retained) < 30 and generated < 600:
                        candidate = generator.generate(rule)
                        generated += 1
                        samples = target_samples([candidate], rule.id, syntax)
                        if samples:
                            retained.extend(samples)
                        else:
                            discarded += 1
                    if len(retained) != 30:
                        raise ValueError(f'Incomplete target sample: {len(retained)}/30; generated={generated}')
                    errors = target_errors = 0
                    examples = []
                    for candidate in retained:
                        result = self.db.execute(conn, candidate.sql)
                        isolation = None
                        if not result['ok']:
                            errors += 1
                            isolation = self.db.execute(conn, candidate.isolation_sql)
                            target_errors += int(not isolation['ok'])
                            examples.append({'sql': candidate.sql, **result, 'isolation': isolation})
                        stream.write(json.dumps({'batch': batch, **asdict(candidate), **result,
                                                 'isolation': isolation}, ensure_ascii=False) + '\n')
                    accuracy = (30 - errors) / 30
                    batches.append({'target_sql': 30, 'generated': generated, 'discarded': discarded,
                                    'accuracy': accuracy, 'target_errors': target_errors, 'errors': examples[:3]})
                    stream.flush()
        finally:
            conn.close()
        verdict = {'rule': asdict(rule), 'passed': all(batch['accuracy'] > .95 and batch['target_errors'] == 0 for batch in batches),
                   'threshold': '>0.95 per batch and zero target-attributed errors', 'batches': batches}
        save(directory / 'verdict.json', verdict)
        return verdict

    def run(self):
        start = time.monotonic()
        prior_elapsed = self.state['elapsed_seconds']
        conn = self.db.connect()
        with conn.cursor() as cursor:
            cursor.execute('SELECT VERSION(), DATABASE(), @@sql_mode')
            version, database, sql_mode = cursor.fetchone()
        conn.close()
        self.event('training_started', pid=os.getpid(), server_version=version,
                   database=database, sql_mode=sql_mode)
        features = [(category, name, text) for category, items in self.corpus.items() for name, text in items.items()]
        visited = 0
        try:
            for category, feature, description in features:
                if feature in self.state['completed_features']:
                    continue
                if self.feature_limit and visited >= self.feature_limit:
                    break
                visited += 1
                self.state['current_feature'] = feature
                feature_id = hashlib.sha256(feature.encode()).hexdigest()[:16]
                feature_dir = self.directory / 'features' / feature_id
                feature_dir.mkdir(parents=True, exist_ok=True)
                print(f'Training feature: {feature}', flush=True)
                self.event('feature_started', feature=feature, category=category)
                accepted_ids = []
                feedback = None
                for refinement in range(4):
                    try:
                        candidates = self.propose(feature, description, feedback)
                        save(feature_dir / f'candidates-{time.time_ns()}.json', [asdict(rule) for rule in candidates])
                    except APIError:
                        raise
                    except Exception as error:
                        feedback = {'generation_error': str(error)}
                        self.event('candidate_generation_failed', feature=feature, error=str(error))
                        continue
                    failed = []
                    for index, rule in enumerate(candidates):
                        trial_dir = feature_dir / f'trial-{time.time_ns()}-{index}'
                        try:
                            verdict = self.evaluate(rule, trial_dir, seed=refinement * 10000 + index)
                        except Exception as error:
                            detail = error.stderr if isinstance(error, subprocess.CalledProcessError) else str(error)
                            verdict = {'passed': False, 'error': detail}
                        self.event('rule_verdict', feature=feature, rule_id=rule.id, **verdict)
                        if verdict['passed']:
                            if rule.id not in {existing.id for existing in self.accepted}:
                                self.accepted.append(rule)
                                save(self.rules_path, [asdict(item) for item in self.accepted])
                            accepted_ids.append(rule.id)
                        else:
                            failed.append({'candidate': asdict(rule), 'feedback': verdict})
                    if not failed:
                        break
                    feedback = failed
                if accepted_ids:
                    if feature not in self.state['completed_features']:
                        self.state['completed_features'].append(feature)
                    if feature in self.state['failed_features']:
                        self.state['failed_features'].remove(feature)
                    save(feature_dir / 'accepted.json', {'feature': feature, 'rule_ids': sorted(set(accepted_ids))})
                else:
                    if feature not in self.state['failed_features']:
                        self.state['failed_features'].append(feature)
                self.state['elapsed_seconds'] = prior_elapsed + time.monotonic() - start
                save(self.state_path, self.state)
                print(f'Feature finished: {feature}; accepted={len(set(accepted_ids))}; completed={len(self.state["completed_features"])}', flush=True)
            full = len(self.state['completed_features']) == len(features) and not self.state['failed_features']
            self.state['status'] = 'completed' if full else 'incomplete'
            compile_rules(ROOT / 'configs/mysql/MySQLBase.g4', self.accepted,
                          self.directory / 'LearnedMySQL.g4')
        except BaseException as error:
            self.state['status'] = 'interrupted' if isinstance(error, KeyboardInterrupt) else 'infrastructure_error'
            self.event('training_error', error=str(error), error_type=type(error).__name__)
            raise
        finally:
            self.state['elapsed_seconds'] = prior_elapsed + time.monotonic() - start
            save(self.state_path, self.state)
            self.event('training_stopped', status=self.state['status'], completed=len(self.state['completed_features']))
