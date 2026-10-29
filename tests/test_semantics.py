import json
from pathlib import Path

import pytest

from lacastv3.generator import SQLGenerator, GenerationFailure
from lacastv3.productions import Rule
from lacastv3.semantics import Column, Scope, Expression, validate_projection

ROOT = Path(__file__).resolve().parents[1]


def test_name_scope_and_alias_shadowing():
    outer = Scope([Column('x', 'id', 'integer')])
    inner = Scope([Column('y', 'price', 'double')], outer)
    assert inner.resolve('x', 'id') == outer.columns[0]
    with pytest.raises(ValueError):
        Scope([Column('x', 'name', 'text')], outer).resolve('x', 'id')
    assert not Scope([Column('x', 'name', 'text')], outer).available('integer')


def test_aggregate_projection_requires_grouping():
    column = Column('t', 'id', 'integer')
    with pytest.raises(ValueError):
        validate_projection([Expression('COUNT(*)', 'integer', True),
                             Expression(column.sql, 'integer', free_columns=frozenset([column]))], set())


def test_generator_preserves_rule_identity_for_every_query_shape():
    schema = [{'key': name, 'fields': ['id'], 'types': ['integer']}
              for name in ('table1', 'table2')]
    constants = json.loads((ROOT / 'configs/mysql/semantics.json').read_text())['types']
    rule = Rule('abs', 'integer', '"ABS(" integerExpr ")"')
    generator = SQLGenerator(schema, constants, [rule])
    for mode in generator.MODES:
        candidate = generator.generate(rule, mode)
        assert 'abs' in candidate.derivation


def test_aggregate_in_aggregate_is_rejected():
    generator = SQLGenerator([], {'integer': ['1']}, [])
    with pytest.raises(GenerationFailure):
        generator.expression(Rule('sum', 'integer', '"SUM(" integerAtom ")"', True), Scope(), allow_aggregate=False)
