import pytest

from lacastv3.queries import Projection, SelectQuery, SetQuery
from lacastv3.semantics import Column, Expression, Scope
from lacastv3.generator import SQLGenerator, GenerationFailure
from lacastv3.productions import Rule


def test_derived_columns_preserve_declared_output_names_and_types():
    column = Column('input', 'price', 'double')
    query = SelectQuery(Scope([column]), 'table1 AS input', (
        Projection(Expression(column.sql, 'double', free_columns=frozenset([column])), 'derived_price'),))
    assert query.output_columns('output') == [Column('output', 'derived_price', 'double')]
    with pytest.raises(ValueError):
        Scope(query.output_columns('output')).resolve('output', 'price')


def test_projection_aliases_and_grouping_are_validated():
    column = Column('t', 'id', 'integer')
    scope = Scope([column])
    scalar = Projection(Expression(column.sql, 'integer', free_columns=frozenset([column])), 'id_value')
    aggregate = Projection(Expression('COUNT(*)', 'integer', True), 'count_value')
    with pytest.raises(ValueError, match='ungrouped'):
        SelectQuery(scope, 'table1 AS t', (scalar, aggregate)).render()
    sql = SelectQuery(scope, 'table1 AS t', (scalar, aggregate), grouping=frozenset([column]),
                      having_alias='count_value', order_aliases=('id_value',)).render()
    assert 'GROUP BY `t`.`id`' in sql and 'HAVING `count_value`' in sql
    with pytest.raises(ValueError, match='unknown projection'):
        SelectQuery(scope, 'table1 AS t', (scalar,), order_aliases=('missing',)).render()


def test_where_cannot_receive_an_aggregate():
    with pytest.raises(ValueError, match='WHERE'):
        SelectQuery(Scope(), '', (Projection(Expression('1', 'integer'), 'a'),),
                    predicate=Expression('COUNT(*) > 0', 'boolean', True)).render()
    with pytest.raises(ValueError, match='WHERE'):
        SelectQuery(Scope(), '', (Projection(Expression('1', 'integer'), 'a'),),
                    predicate=Expression('ROW_NUMBER() OVER () > 0', 'boolean', window=True)).render()


def test_set_operations_require_matching_projection_shapes():
    left = SelectQuery(Scope(), '', (Projection(Expression('1', 'integer'), 'a'),))
    wrong_type = SelectQuery(Scope(), '', (Projection(Expression("'x'", 'text'), 'a'),))
    wrong_width = SelectQuery(Scope(), '', (Projection(Expression('1', 'integer'), 'a'),
                                          Projection(Expression('2', 'integer'), 'b')))
    for right in (wrong_type, wrong_width):
        with pytest.raises(ValueError, match='arity and type'):
            SetQuery(left, right).render()


def test_window_arguments_remain_free_and_cannot_be_grouped_away(monkeypatch):
    generator = SQLGenerator([], {'double': ['1.0']}, [])
    monkeypatch.setattr(generator.random, 'random', lambda: 0.0)
    column = Column('t', 'price', 'double')
    window = generator.expression(Rule('win', 'double', '"AVG(" doubleAtom ") OVER ()"', True), Scope([column]))
    assert window.window and not window.aggregate and window.free_columns == {column}
    projections = (Projection(window, 'w'), Projection(Expression('COUNT(*)', 'integer', True), 'n'))
    with pytest.raises(ValueError, match='ungrouped'):
        SelectQuery(Scope([column]), 'table1 AS t', projections).render()
    with pytest.raises(ValueError, match='window output'):
        SelectQuery(Scope([column]), 'table1 AS t', (Projection(window, 'w'),), having_alias='w').render()


def test_aggregate_arguments_cannot_contain_window_calls(monkeypatch):
    window_rule = Rule('window', 'integer', '"ROW_NUMBER() OVER ()"')
    generator = SQLGenerator([], {'integer': ['1']}, [window_rule])
    monkeypatch.setattr(generator.random, 'random', lambda: 0.0)
    with pytest.raises(GenerationFailure, match='aggregate arguments'):
        generator.expression(Rule('sum', 'integer', '"SUM(" integerExpr ")"', True), Scope())
