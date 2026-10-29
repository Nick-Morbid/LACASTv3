import json
from pathlib import Path

from lacastv3.features import feature_key, normalize_events, upgrade_state

ROOT = Path(__file__).resolve().parents[1]


def test_all_189_corpus_entries_have_distinct_identity():
    corpus = json.loads((ROOT / 'configs/mysql/web_corpus.json').read_text(encoding='utf-8'))
    keys = [feature_key(category, name) for category, items in corpus.items() for name in items]
    assert len(keys) == len(set(keys)) == 189


def test_legacy_completion_does_not_complete_another_category():
    events = normalize_events([
        {'event': 'feature_started', 'category': 'Assignment Operators', 'feature': '='},
        {'event': 'rule_verdict', 'feature': '=', 'passed': True, 'rule_id': 'r'},
    ])
    state = upgrade_state({'completed_features': ['='], 'failed_features': []}, events)
    assert state['completed_features'] == ['Assignment Operators::=']
    assert feature_key('Comparison Functions and Operators', '=') not in state['completed_features']
    assert events[1]['feature_key'] == 'Assignment Operators::='
