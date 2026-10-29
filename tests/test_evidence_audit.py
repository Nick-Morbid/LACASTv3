from dataclasses import asdict
import json
from pathlib import Path

import pytest

from lacastv3.audit import verify_trial
from lacastv3.compiler import compile_rules
from lacastv3.productions import Rule

ROOT = Path(__file__).resolve().parents[1]


def make_trial(directory, change=None):
    rule = Rule('audit-abs', 'integer', '"ABS(" integerAtom ")"')
    compile_rules(ROOT / 'configs/mysql/MySQLBase.g4', [rule], directory / 'LearnedMySQL.g4')
    records = [{'batch': batch, 'sql': 'SELECT (ABS(-2));', 'derivation': [rule.id],
                'ok': True, 'isolation': None} for batch in range(3) for _ in range(30)]
    if change:
        change(records)
    (directory / 'sql_results.jsonl').write_text('\n'.join(json.dumps(record) for record in records))
    (directory / 'verdict.json').write_text(json.dumps({'rule': asdict(rule), 'passed': True,
        'batches': [{'accuracy': 1, 'target_sql': 30, 'target_errors': 0} for _ in range(3)]}))
    return rule


def test_audit_replays_target_context_and_all_batches(tmp_path):
    rule = make_trial(tmp_path)
    result = verify_trial(tmp_path, rule, tmp_path / 'cache')
    assert [batch['target_sql'] for batch in result['batches']] == [30, 30, 30]


@pytest.mark.parametrize('change', [
    lambda records: records.pop(),
    lambda records: records[0].update(derivation=[]),
    lambda records: records[0].update(sql='SELECT 1;'),
    lambda records: records[0].update(ok=False),
])
def test_audit_rejects_incomplete_or_unrelated_or_failed_evidence(tmp_path, change):
    rule = make_trial(tmp_path, change)
    with pytest.raises(ValueError):
        verify_trial(tmp_path, rule, tmp_path / 'cache')


def test_audit_rejects_grammar_rule_replacement(tmp_path):
    rule = make_trial(tmp_path)
    path = tmp_path / 'LearnedMySQL.g4'
    path.write_text(path.read_text().replace("learnedRule0: 'ABS'", "learnedRule0: 'SIN'"))
    with pytest.raises(ValueError, match='saved target production'):
        verify_trial(tmp_path, rule, tmp_path / 'cache')
