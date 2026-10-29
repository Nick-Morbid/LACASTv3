from types import SimpleNamespace

from lacastv3.productions import Rule
from lacastv3.training import Trainer


class Connection:
    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql):
        pass

    def fetchone(self):
        return ('8.4.11', 'lacastv3_test', 'ONLY_FULL_GROUP_BY')

    def close(self):
        pass


def test_refinement_reuses_passed_candidate_but_evaluates_repair(tmp_path, monkeypatch):
    trainer = Trainer(tmp_path, SimpleNamespace(connect=Connection))
    trainer.corpus = {'math': {'ABS(x)': 'absolute value'}}
    good = Rule('good', 'integer', '"ABS(" integerAtom ")"')
    bad = Rule('bad', 'double', '"ABS(bad_column)"')
    repair = Rule('repair', 'double', '"ABS(" doubleAtom ")"')
    responses = iter(([good, bad], [good, repair]))
    monkeypatch.setattr(trainer, 'propose', lambda *args: next(responses))
    evaluated = []

    def evaluate(rule, *args, **kwargs):
        evaluated.append(rule.id)
        return {'passed': rule.id != 'bad'}

    monkeypatch.setattr(trainer, 'evaluate', evaluate)
    trainer.run()
    assert evaluated == ['good', 'bad', 'repair']
    assert {rule.id for rule in trainer.accepted} == {'good', 'repair'}
    assert trainer.state['completed_features'] == ['math::ABS(x)']
    assert trainer.state['status'] == 'completed'
