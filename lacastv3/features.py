"""Corpus entries are identified by category and signature, not signature alone."""
import hashlib
import json
from pathlib import Path


def feature_key(category, name):
    return f'{category}::{name}'


def feature_directory(root: Path, key: str):
    return root / 'features' / hashlib.sha256(key.encode()).hexdigest()[:16]


def normalize_events(events):
    result = []
    current = None
    for original in events:
        event = dict(original)
        if event['event'] == 'feature_started':
            current = (event['feature'], feature_key(event['category'], event['feature']))
        if 'feature' in event and 'feature_key' not in event and current and current[0] == event['feature']:
            event['feature_key'] = current[1]
        result.append(event)
    return result


def upgrade_state(state, events):
    result = dict(state)
    if result.get('schema_version', 1) >= 2:
        return result
    known = {event['feature']: event['feature_key'] for event in events
             if event['event'] == 'feature_started'}
    for column in ('completed_features', 'failed_features'):
        # Only the entry actually visited is migrated. A duplicate signature in
        # another category remains pending and must be trained independently.
        result[column] = [known[name] for name in state[column]]
    result['schema_version'] = 2
    return result


def migrate_feature_directories(root, events):
    known = {event['feature']: event['feature_key'] for event in events
             if event['event'] == 'feature_started'}
    for name, key in known.items():
        old = root / 'features' / hashlib.sha256(name.encode()).hexdigest()[:16]
        new = feature_directory(root, key)
        if old.exists():
            expected_parent = (root / 'features').resolve()
            if old.resolve().parent != expected_parent or new.resolve().parent != expected_parent:
                raise ValueError('Feature migration paths escaped the feature directory')
            if new.exists():
                raise FileExistsError(f'Conflicting old and new feature directories: {new}')
            old.rename(new)
        accepted = new / 'accepted.json'
        if accepted.exists():
            data = json.loads(accepted.read_text())
            data['feature_key'] = key
            temporary = accepted.with_suffix('.tmp')
            temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
            temporary.replace(accepted)
