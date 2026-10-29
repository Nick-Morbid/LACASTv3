"""Explicit SQL type, name-resolution, and aggregation context."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Column:
    relation: str
    name: str
    datatype: str

    @property
    def sql(self):
        return f'`{self.relation}`.`{self.name}`'


@dataclass
class Scope:
    columns: list[Column] = field(default_factory=list)
    parent: 'Scope | None' = None

    def available(self, datatype: str):
        local = [column for column in self.columns if column.datatype == datatype]
        shadowed = {column.relation for column in self.columns}
        return local + ([column for column in self.parent.available(datatype)
                         if column.relation not in shadowed] if self.parent else [])

    def resolve(self, relation: str, name: str):
        for column in self.columns:
            if (column.relation, column.name) == (relation, name):
                return column
        if self.parent and not any(column.relation == relation for column in self.columns):
            return self.parent.resolve(relation, name)
        raise ValueError(f'Column is not visible: {relation}.{name}')


@dataclass(frozen=True)
class Expression:
    sql: str
    datatype: str
    aggregate: bool = False
    rule_ids: tuple[str, ...] = ()
    free_columns: frozenset[Column] = frozenset()


def validate_projection(expressions: list[Expression], grouping: set[Column]):
    if grouping or any(expression.aggregate for expression in expressions):
        for expression in expressions:
            if not expression.free_columns.issubset(grouping):
                raise ValueError('Non-aggregate projection contains an ungrouped column')
