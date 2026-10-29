import json
from types import SimpleNamespace

from lacastv3 import revalidate


class Connection:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def cursor(self):
        return self

    def execute(self, sql):
        pass

    def fetchone(self):
        return ('8.4.11', 'lacastv3_test', 'ONLY_FULL_GROUP_BY')


def test_revalidation_preserves_source_and_requires_independent_audit(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir()
    snapshot = b'[{"id":"one"},{"id":"two"}]'
    (source / 'trained_rules.json').write_bytes(snapshot)

    class Trainer:
        def __init__(self, output, db, generation_profile):
            assert generation_profile == 'expanded'
            assert (output / 'trained_rules.json').read_bytes() == snapshot
            self.accepted = [SimpleNamespace(id='one'), SimpleNamespace(id='two')]

        def evaluate(self, rule, trial, seed):
            return {'passed': True}

    monkeypatch.setattr(revalidate, 'Trainer', Trainer)

    def audit(trial, rule, cache):
        if rule.id == 'two':
            raise ValueError('target absent from parser evidence')
        return {'rule_id': rule.id}

    monkeypatch.setattr(revalidate, 'verify_trial', audit)
    output = tmp_path / 'output'
    revalidate.run_revalidation(source, output, SimpleNamespace(connect=Connection))
    summary = json.loads((output / 'summary.json').read_text())
    assert summary['checked'] == 2 and summary['passed'] == 1
    assert not summary['full_snapshot_verified']
    assert (source / 'trained_rules.json').read_bytes() == snapshot
    assert list(source.iterdir()) == [source / 'trained_rules.json']
