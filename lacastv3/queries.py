"""SQL query structure and output schemas, independent of grammar annotations."""
from dataclasses import dataclass

from .semantics import Column, Expression, Scope, validate_projection


def quote(name):
    return '`' + name.replace('`', '``') + '`'


@dataclass(frozen=True)
class Projection:
    expression: Expression
    alias: str


@dataclass(frozen=True)
class SelectQuery:
    scope: Scope
    source: str
    projections: tuple[Projection, ...]
    predicate: Expression | None = None
    grouping: frozenset[Column] = frozenset()
    having_alias: str | None = None
    order_aliases: tuple[str, ...] = ()
    limit: int = 5

    def validate(self):
        aliases = [projection.alias for projection in self.projections]
        if not aliases or len(aliases) != len(set(aliases)):
            raise ValueError('Projection aliases must be present and unique')
        if not 0 <= self.limit <= 1000:
            raise ValueError('Query limit must be bounded')
        if self.predicate and (self.predicate.aggregate or self.predicate.window):
            raise ValueError('Aggregate/window expression cannot appear in WHERE')
        expressions = [projection.expression for projection in self.projections]
        validate_projection(expressions, set(self.grouping))
        for expression in expressions + ([self.predicate] if self.predicate else []):
            for column in expression.free_columns:
                if self.scope.resolve(column.relation, column.name) != column:
                    raise ValueError('Column type does not agree with its visible binding')
        for column in self.grouping:
            if self.scope.resolve(column.relation, column.name) != column:
                raise ValueError('Grouping column is not in scope')
        if not set(self.order_aliases).issubset(aliases):
            raise ValueError('ORDER BY references an unknown projection alias')
        if self.having_alias is not None and self.having_alias not in aliases:
            raise ValueError('HAVING references an unknown projection alias')
        if self.having_alias is not None and next(item.expression for item in self.projections
                                                  if item.alias == self.having_alias).window:
            raise ValueError('HAVING cannot refer to a window output at the same query level')

    def render(self, include_limit=True):
        self.validate()
        sql = 'SELECT ' + ', '.join(projection.expression.sql + ' AS ' + quote(projection.alias)
                                   for projection in self.projections)
        if self.source:
            sql += ' FROM ' + self.source
        if self.predicate:
            sql += ' WHERE ' + self.predicate.sql
        if self.grouping:
            sql += ' GROUP BY ' + ', '.join(sorted(column.sql for column in self.grouping))
        if self.having_alias:
            sql += ' HAVING ' + quote(self.having_alias) + ' IS NOT NULL'
        if self.order_aliases:
            sql += ' ORDER BY ' + ', '.join(map(quote, self.order_aliases))
        if include_limit:
            sql += f' LIMIT {self.limit}'
        return sql

    def output_columns(self, relation):
        self.validate()
        return [Column(relation, item.alias, item.expression.datatype) for item in self.projections]

    @property
    def output_types(self):
        return tuple(item.expression.datatype for item in self.projections)

    @property
    def rule_ids(self):
        return tuple(rule for item in self.projections for rule in item.expression.rule_ids) + (
            self.predicate.rule_ids if self.predicate else ())


@dataclass(frozen=True)
class SetQuery:
    left: SelectQuery
    right: SelectQuery
    operator: str = 'UNION ALL'
    limit: int = 5

    def render(self):
        if self.operator not in ('UNION', 'UNION ALL', 'INTERSECT', 'EXCEPT'):
            raise ValueError('Unsupported set operator')
        if self.left.output_types != self.right.output_types:
            raise ValueError('Set-operation projections must agree in arity and type')
        if self.left.order_aliases or self.right.order_aliases:
            raise ValueError('Set branches must not have unparenthesized ORDER BY')
        if not 0 <= self.limit <= 1000:
            raise ValueError('Set-operation limit must be bounded')
        return self.left.render(False) + ' ' + self.operator + ' ' + self.right.render(False) + f' LIMIT {self.limit}'
