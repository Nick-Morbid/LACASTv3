"""Varied projections and derived-column bindings over the typed expression generator."""
from .coverage import GeneratedSQL
from .generator import SQLGenerator
from .queries import Projection, SelectQuery, SetQuery, quote
from .semantics import Expression, Scope


class ContextSQLGenerator(SQLGenerator):
    MODES = SQLGenerator.MODES + ('having',)

    def extra_projections(self, scope):
        return tuple(Projection(self.atom(self.random.choice(list(self.constants)), scope), f'aux{index}')
                     for index in range(self.random.randint(0, 2)))

    def generate(self, target, mode=None):
        mode = mode or self.random.choice(self.MODES)
        table = self.schema[0]
        scope = self.scope(table, 't0')
        source = f'{quote(table["key"])} AS `t0`'
        prefix = ''
        if mode == 'join':
            other = self.schema[1]
            scope.columns += self.scope(other, 't1').columns
            right = f'{quote(other["key"])} AS `t1`'
            kind = self.random.choice(('JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'CROSS JOIN', 'NATURAL JOIN', 'USING'))
            if kind == 'USING':
                source += f' JOIN {right} USING (`id`)'
            elif kind in ('CROSS JOIN', 'NATURAL JOIN'):
                source += f' {kind} {right}'
            else:
                source += f' {kind} {right} ON `t0`.`id` = `t1`.`id`'
        elif mode in ('cte', 'derived'):
            inner_scope = self.scope(table, 'input_table')
            projections = []
            for index, column in enumerate(inner_scope.columns):
                # Derived outputs have their own names and SQL types. A real
                # computed output also tests binding beyond SELECT * passthrough.
                sql = f'({column.sql} + 1)' if column.datatype == 'integer' else column.sql
                projections.append(Projection(Expression(sql, column.datatype,
                    free_columns=frozenset([column])), f'd{index}'))
            inner = SelectQuery(inner_scope, f'{quote(table["key"])} AS `input_table`', tuple(projections))
            scope = Scope(inner.output_columns('t0'))
            if mode == 'cte':
                prefix = f'WITH input_rows AS ({inner.render(False)}) '
                source = 'input_rows AS `t0`'
            else:
                source = f'({inner.render(False)}) AS `t0`'

        if mode in ('scalar_subquery', 'exists'):
            inner_scope = self.scope(self.schema[1], 't1', parent=None if target.aggregate else scope)
            expression = self.expression(target, inner_scope)
            inner = SelectQuery(inner_scope, f'{quote(self.schema[1]["key"])} AS `t1`',
                                (Projection(expression, 'inner_result'),), limit=1)
            if mode == 'scalar_subquery':
                value = Expression('(' + inner.render() + ')', expression.datatype,
                    rule_ids=expression.rule_ids,
                    free_columns=frozenset(column for column in expression.free_columns if column.relation == 't0'))
                projections = (Projection(value, 'result'),) + self.extra_projections(scope)
                predicate = None
            else:
                value = Expression('EXISTS (' + inner.render() + ')', 'boolean',
                    rule_ids=expression.rule_ids,
                    free_columns=frozenset(column for column in expression.free_columns if column.relation == 't0'))
                projections = (Projection(self.atom('integer', scope), 'result'),) + self.extra_projections(scope)
                predicate = value
            query = SelectQuery(scope, source, projections, predicate=predicate)
            isolation_source = source + f' JOIN {quote(self.schema[1]["key"])} AS `t1` ON `t0`.`id` = `t1`.`id`'
        else:
            expression = self.expression(target, scope)
            projections = (Projection(expression, 'result'),) + self.extra_projections(scope)
            predicate = None
            if mode == 'predicate' and not expression.aggregate and not expression.window:
                predicate = Expression(expression.sql + ' IS NOT NULL', 'boolean',
                    rule_ids=expression.rule_ids, free_columns=expression.free_columns)
                projections = (Projection(self.atom('integer', scope), 'result'),) + self.extra_projections(scope)
            grouped = mode in ('group', 'having') or any(item.expression.aggregate for item in projections)
            grouping = frozenset(column for item in projections for column in item.expression.free_columns) if grouped else frozenset()
            having_alias = 'result' if mode == 'having' else None
            if mode == 'having' and expression.window:
                # Window outputs are unavailable to HAVING at this query level.
                projections += (Projection(Expression('1', 'integer'), 'having_guard'),)
                having_alias = 'having_guard'
            query = SelectQuery(scope, source, projections, predicate=predicate, grouping=grouping,
                having_alias=having_alias,
                order_aliases=('result',) if mode == 'order' else ())
            isolation_source = source

        if mode == 'union':
            right = SelectQuery(Scope(), '', tuple(Projection(self.atom(dtype, Scope()), f'right{index}')
                                                for index, dtype in enumerate(query.output_types)))
            sql = SetQuery(query, right, self.random.choice(('UNION ALL', 'UNION', 'INTERSECT', 'EXCEPT'))).render()
            derivation = query.rule_ids + right.rule_ids
        else:
            sql = query.render()
            derivation = query.rule_ids
        isolation = f'{prefix}SELECT {expression.sql} AS result FROM {isolation_source} LIMIT 5;'
        return GeneratedSQL(prefix + sql + ';', derivation, isolation)
