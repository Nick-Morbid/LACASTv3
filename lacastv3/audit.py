"""Recompute acceptance from retained SQL, exact parser contexts, and DB evidence."""
from collections import defaultdict
from dataclasses import asdict
import json
from pathlib import Path

from .parser import SQLParser
from .compiler import compile_rules
from .productions import Rule
from .features import feature_key, normalize_events, upgrade_state
from .training import ROOT, save


def verify_trial(trial: Path, rule: Rule, cache: Path):
    verdict = json.loads((trial / 'verdict.json').read_text())
    if verdict.get('rule') != asdict(rule) or not verdict.get('passed'):
        raise ValueError('Trial verdict does not accept the exact saved rule')
    expected_grammar = cache / 'definitions' / rule.id / 'ExpectedMySQL.g4'
    compile_rules(ROOT / 'configs/mysql/MySQLBase.g4', [rule], expected_grammar)
    expected_definition = next(line for line in expected_grammar.read_text().splitlines()
                               if line.startswith('learnedRule0:'))
    actual_definition = next(line for line in (trial / 'LearnedMySQL.g4').read_text().splitlines()
                             if line.startswith('learnedRule0:'))
    if expected_definition != actual_definition:
        raise ValueError('Retained grammar does not contain the saved target production')
    parser = SQLParser(trial / 'LearnedMySQL.g4', ROOT / 'vendor/antlr-4.13.2-complete.jar',
                       cache, {'learnedRule0': rule.id})
    records = [json.loads(line) for line in (trial / 'sql_results.jsonl').read_text(encoding='utf-8').splitlines()]
    batches = defaultdict(list)
    for record in records:
        if rule.id not in record['derivation']:
            raise ValueError('Unrelated SQL was included in the accuracy denominator')
        if rule.id not in parser.parse(record['sql']).rule_ids:
            raise ValueError('SQL parse does not contain the target production')
        batches[record['batch']].append(record)
    if set(batches) != {0, 1, 2}:
        raise ValueError('Expected exactly three execution batches')
    checked = []
    for index in range(3):
        batch = batches[index]
        if len(batch) != 30:
            raise ValueError('Expected exactly 30 target-confirmed executions per batch')
        errors = [record for record in batch if not record['ok']]
        accuracy = (len(batch) - len(errors)) / len(batch)
        target_errors = sum(not (record.get('isolation') or {}).get('ok', False) for record in errors)
        if accuracy <= .95 or target_errors:
            raise ValueError(f'Batch {index} does not meet the fixed acceptance contract')
        recorded = verdict['batches'][index]
        if recorded['accuracy'] != accuracy or recorded['target_sql'] != 30 or recorded['target_errors'] != target_errors:
            raise ValueError('Stored summary disagrees with retained execution evidence')
        checked.append({'batch': index, 'target_sql': 30, 'accuracy': accuracy,
                        'target_errors': target_errors})
    return {'rule_id': rule.id, 'trial': str(trial.resolve()), 'batches': checked}


def run_audit(source: Path, output: Path, allow_partial=False):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    rules = [Rule(**item) for item in json.loads((source / 'trained_rules.json').read_text())]
    state = json.loads((source / 'training_state.json').read_text())
    events = normalize_events([json.loads(line) for line in (source / 'events.jsonl').read_text(encoding='utf-8').splitlines()])
    state = upgrade_state(state, events)
    candidates = defaultdict(list)
    for path in (source / 'features').glob('*/trial-*/verdict.json'):
        verdict = json.loads(path.read_text())
        if verdict.get('passed'):
            candidates[verdict['rule']['id']].append(path.parent)
    checked = []
    failed = []
    for rule in rules:
        failures = []
        for trial in candidates[rule.id]:
            try:
                checked.append(verify_trial(trial, rule, source / 'parser_cache'))
                break
            except Exception as error:
                failures.append(str(error))
        else:
            failed.append({'rule_id': rule.id, 'errors': failures or ['No successful retained trial']})
    corpus = json.loads((ROOT / 'configs/mysql/web_corpus.json').read_text(encoding='utf-8'))
    expected = {feature_key(category, name) for category, entries in corpus.items() for name in entries}
    completed = set(state['completed_features'])
    feature_links = {}
    legacy_keys = {event['feature']: event['feature_key'] for event in events if event['event'] == 'feature_started'}
    for path in (source / 'features').glob('*/accepted.json'):
        data = json.loads(path.read_text())
        key = data.get('feature_key') or legacy_keys[data['feature']]
        feature_links[key] = set(data['rule_ids'])
    accepted_ids = {item.id for item in rules}
    missing_links = sorted(feature for feature in completed
                           if not feature_links.get(feature) or not feature_links[feature].issubset(accepted_ids))
    terminal = [event for event in events if event['event'] in ('training_started', 'training_stopped')]
    natural_completion = bool(terminal and terminal[-1]['event'] == 'training_stopped'
                              and terminal[-1].get('status') == 'completed')
    complete = (completed == expected and not state['failed_features']
                and not failed and not missing_links and state['status'] == 'completed' and natural_completion)
    result = {'source': str(source.resolve()), 'full_run_verified': complete,
              'rules_checked': len(rules), 'rules_verified': len(checked),
              'corpus_items': len(expected), 'completed_features': len(completed),
              'failed_features': state['failed_features'], 'missing_feature_links': missing_links,
              'terminal_completion_recorded': natural_completion,
              'rule_failures': failed, 'verified_rule_evidence': checked,
              'scope': 'Recomputed retained execution evidence and replayed exact ANTLR target contexts.'}
    save(output / 'audit.json', result)
    print(json.dumps({key: value for key, value in result.items() if key != 'verified_rule_evidence'}, indent=2))
    if failed or missing_links or (not allow_partial and not complete):
        raise RuntimeError('Training evidence audit is incomplete or failed')
    return result
