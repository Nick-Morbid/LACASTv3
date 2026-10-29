import pytest
import json

from lacastv3 import reconcile
from lacastv3.reconcile import assert_stopped
from lacastv3.features import feature_directory


@pytest.mark.parametrize('state,events', [
    ({'status': 'running'}, [{'event': 'training_stopped'}]),
    ({'status': 'completed'}, [{'event': 'training_stopped'}, {'event': 'training_started'}]),
    ({'status': 'completed'}, []),
])
def test_live_or_unproven_writer_cannot_import(state, events):
    with pytest.raises(ValueError, match='stopped trainer'):
        assert_stopped(state, events)


def test_terminal_training_can_import_independent_evidence():
    assert_stopped({'status': 'completed'}, [{'event': 'training_started'}, {'event': 'training_stopped'}])


def test_import_updates_rule_links_and_checkpoints_old_evidence(tmp_path, monkeypatch):
    directory = tmp_path / 'training'
    directory.mkdir()
    key = 'math::ABS(x)'
    old = {'id': 'old', 'return_type': 'integer', 'production': '"ABS(" integerAtom ")"'}
    new = {'id': 'new', 'return_type': 'integer', 'production': '"ABS(" integerAtom ") + 0"'}
    (directory / 'training_state.json').write_text(json.dumps({'status': 'completed', 'completed_features': [key]}))
    (directory / 'events.jsonl').write_text('{"event":"training_stopped","status":"completed"}\n')
    (directory / 'trained_rules.json').write_text(json.dumps([old]))
    feature = feature_directory(directory, key)
    feature.mkdir(parents=True)
    (feature / 'accepted.json').write_text(json.dumps({'feature': 'ABS(x)', 'feature_key': key, 'rule_ids': ['old']}))
    trial = tmp_path / 'verified-trial'
    trial.mkdir()
    (trial / 'verdict.json').write_text(json.dumps({'rule': new, 'passed': True, 'generation_profile': 'expanded'}))
    checked = []
    monkeypatch.setattr(reconcile, 'verify_trial', lambda path, rule, cache: checked.append((path, rule.id)))
    reconcile.import_evidence(directory, trial, key, replaces='old')
    assert [item['id'] for item in json.loads((directory / 'trained_rules.json').read_text())] == ['new']
    assert json.loads((feature / 'accepted.json').read_text())['rule_ids'] == ['new']
    assert len(checked) == 2
    assert list((directory / 'checkpoints').glob('*/before-import.zip'))
    assert (trial / 'verdict.json').exists()
