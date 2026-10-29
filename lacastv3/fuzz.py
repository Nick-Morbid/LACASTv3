"""Execute every generated query and retain syntax and execution failures."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from .compiler import compile_rules
from .profiles import generator_class
from .parser import SQLParser, ParseFailure
from .productions import Rule
from .training import ROOT, save


def run_fuzz(source: Path, output: Path, db, count=10000, seed=0, generation_profile='expanded'):
    if count < 1:
        raise ValueError('Count must be positive')
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite an existing result: {output}')
    rules = [Rule(**item) for item in json.loads((source / 'trained_rules.json').read_text())]
    if not rules:
        raise ValueError('No learned rules available for fuzzing')
    output.mkdir(parents=True)
    grammar = output / 'LearnedMySQL.g4'
    mapping = compile_rules(ROOT / 'configs/mysql/MySQLBase.g4', rules, grammar)
    syntax = SQLParser(grammar, ROOT / 'vendor/antlr-4.13.2-complete.jar', output / 'parser', mapping)
    generator = generator_class(generation_profile)(json.loads((ROOT / 'configs/mysql/schema.json').read_text()),
        json.loads((ROOT / 'configs/mysql/semantics.json').read_text())['types'], rules, seed=seed)
    conn = db.connect()
    with conn.cursor() as cursor:
        cursor.execute('SELECT VERSION(), DATABASE()')
        version, database = cursor.fetchone()
    manifest = {'started_at': datetime.now(timezone.utc).isoformat(), 'server_version': version,
                'database': database, 'source': str(source.resolve()), 'seed': seed, 'count': count,
                'generation_profile': generation_profile,
                'grammar_sha256': hashlib.sha256(grammar.read_bytes()).hexdigest(),
                'rules_sha256': hashlib.sha256((source / 'trained_rules.json').read_bytes()).hexdigest()}
    save(output / 'manifest.json', manifest)
    started = time.monotonic()
    executed = passed = syntax_errors = 0
    status = 'running'
    try:
        with (output / 'sql_results.jsonl').open('w', encoding='utf-8') as stream:
            for index in range(count):
                rule = generator.random.choice(rules)
                # A generation exception stops the run. It must not disappear
                # from the report or be replaced by a silently resampled query.
                candidate = generator.generate(rule)
                parse_error = None
                try:
                    syntax.parse(candidate.sql)
                except ParseFailure as error:
                    parse_error = str(error)
                    syntax_errors += 1
                result = db.execute(conn, candidate.sql)
                executed += 1
                passed += int(result['ok'])
                stream.write(json.dumps({'index': index + 1, **asdict(candidate),
                    'antlr_error': parse_error, **result}, ensure_ascii=False) + '\n')
                if executed % 100 == 0:
                    stream.flush()
                    print(f'{executed}/{count} execution_success={passed/executed:.4%}', flush=True)
        status = 'completed'
    except BaseException:
        status = 'failed'
        raise
    finally:
        conn.close()
        save(output / 'summary.json', {'status': status, 'requested': count,
            'executed': executed, 'passed': passed, 'errors': executed-passed,
            'accuracy': passed/executed if executed else None,
            'antlr_errors': syntax_errors, 'elapsed_seconds': time.monotonic()-started,
            'definition': 'Database execution success; all generated SQL retained, no target filtering.'})
