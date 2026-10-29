"""Import independently verified rule evidence after the trainer has stopped."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

from .audit import verify_trial
from .compiler import compile_rules
from .feature_contract import validate_feature
from .features import feature_directory
from .productions import Rule
from .training import ROOT, exclusive_run, save


def assert_stopped(state, events):
    terminal = [event for event in events if event['event'] in ('training_started', 'training_stopped')]
    if state.get('status') == 'running' or not terminal or terminal[-1]['event'] != 'training_stopped':
        raise ValueError('Evidence import requires a stopped trainer and its terminal record')


def import_evidence(directory: Path, trial: Path, key: str, replaces=None):
    with exclusive_run(directory):
        state = json.loads((directory / 'training_state.json').read_text())
        events = [json.loads(line) for line in (directory / 'events.jsonl').read_text(encoding='utf-8').splitlines()]
        assert_stopped(state, events)
        if key not in state['completed_features']:
            raise ValueError('Imports must supplement an already completed feature')
        verdict = json.loads((trial / 'verdict.json').read_text())
        rule = Rule(**verdict['rule'])
        verify_trial(trial, rule, directory / 'parser_cache')
        rules = [Rule(**item) for item in json.loads((directory / 'trained_rules.json').read_text())]
        if replaces and replaces not in {item.id for item in rules}:
            raise ValueError('The rule to replace is absent')
        requested = feature_directory(directory, key) / 'accepted.json'
        if not requested.exists():
            raise ValueError('Completed feature is missing its accepted-rule mapping')
        updates = {}
        for path in (directory / 'features').glob('*/accepted.json'):
            data = json.loads(path.read_text())
            if path == requested or (replaces and replaces in data['rule_ids']):
                validate_feature(data['feature'], rule)
                ids = set(data['rule_ids'])
                ids.discard(replaces)
                ids.add(rule.id)
                data['rule_ids'] = sorted(ids)
                updates[path] = data
        if not updates:
            raise ValueError('No matching feature mappings')
        checkpoint = directory / 'checkpoints' / ('import-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        checkpoint.mkdir(parents=True)
        with ZipFile(checkpoint / 'before-import.zip', 'x', compression=ZIP_DEFLATED) as archive:
            for path in [directory / 'trained_rules.json', directory / 'training_state.json',
                         directory / 'events.jsonl', *updates]:
                archive.write(path, path.relative_to(directory).as_posix())
        for path in updates:
            destination = path.parent / ('trial-import-' + rule.id + '-' + checkpoint.name)
            shutil.copytree(trial, destination)
            verify_trial(destination, rule, directory / 'parser_cache')
        retained = [item for item in rules if item.id != replaces and item.id != rule.id] + [rule]
        # Compile before updating the authoritative files. A failed compile
        # leaves the previous rules/mappings intact and a recoverable checkpoint.
        compile_rules(ROOT / 'configs/mysql/MySQLBase.g4', retained, checkpoint / 'LearnedMySQL.g4')
        save(directory / 'trained_rules.json', [asdict(item) for item in retained])
        for path, data in updates.items():
            save(path, data)
        shutil.copy2(checkpoint / 'LearnedMySQL.g4', directory / 'LearnedMySQL.g4')
        event = {'time': datetime.now(timezone.utc).isoformat(), 'event': 'rule_evidence_imported',
                 'rule_id': rule.id, 'replaces_rule_id': replaces, 'feature_keys': [data['feature_key'] for data in updates.values()],
                 'source_trial': str(trial.resolve()), 'generation_profile': verdict.get('generation_profile', 'baseline'),
                 'checkpoint': str(checkpoint.relative_to(directory))}
        with (directory / 'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + '\n')
        return event
