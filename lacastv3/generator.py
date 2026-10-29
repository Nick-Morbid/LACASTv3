"""SQL generation is independent from ANTLR's syntax recognition."""
import random
import re

from .coverage import GeneratedSQL
from .productions import Rule
from .compiler import SQL_TOKENS
from .semantics import Column, Expression, Scope, validate_projection
from .regex_patterns import regex_pattern, mysql_string


class GenerationFailure(ValueError):
    pass


class SQLGenerator:
    MODES = ('projection', 'predicate', 'order', 'group', 'join', 'cte',
             'derived', 'scalar_subquery', 'exists', 'union')

    def __init__(self, schema: list[dict], constants: dict[str, list[str]],
                 rules: list[Rule], seed: int = 0, max_depth: int = 2):
        self.schema = schema
        self.constants = constants
        self.rules = rules
        self.random = random.Random(seed)
        self.max_depth = max_depth

    def scope(self, table, alias, parent=None):
        return Scope([Column(alias, field, dtype) for field, dtype in
                      zip(table['fields'], table['types'])], parent)

    def atom(self, dtype, scope):
        if dtype == 'regexpattern':
            return Expression(mysql_string(regex_pattern(self.random)), 'char')
        if dtype == 'any':
            dtype = self.random.choice(list(self.constants))
        if dtype not in self.constants:
            raise GenerationFailure(f'Unsupported SQL type: {dtype}')
        columns = scope.available(dtype)
        if columns and self.random.random() < 0.5:
            column = self.random.choice(columns)
            return Expression(column.sql, dtype, free_columns=frozenset([column]))
        return Expression(self.random.choice(self.constants[dtype]), dtype)

    def expression(self, rule, scope, depth=0, allow_aggregate=True):
        if rule.aggregate and not allow_aggregate:
            raise GenerationFailure('Nested aggregate calls are not legal')
        pieces = []

        def expand(node):
            if node.kind == 'literal':
                return node.value
            if node.kind == 'reference':
                match = re.fullmatch(r'([a-z]+)(Atom|Expr)', node.value)
                if not match:
                    raise GenerationFailure(f'Unknown operand: {node.value}')
                dtype, category = match.groups()
                candidates = [r for r in self.rules if r.return_type == dtype and
                              not r.aggregate]
                if category == 'Expr' and depth < self.max_depth and candidates and self.random.random() < .4:
                    expression = self.expression(self.random.choice(candidates), scope,
                                                 depth + 1, allow_aggregate=False)
                else:
                    expression = self.atom(dtype, scope)
                pieces.append(expression)
                return expression.sql
            if node.kind == 'sequence':
                return ' '.join(expand(child) for child in node.children)
            if node.kind == 'choice':
                return expand(self.random.choice(node.children))
            if node.kind == 'repeat':
                minimum = 1 if node.value == '+' else 0
                maximum = 1 if node.value == '?' else 2
                return ' '.join(expand(node.children[0]) for _ in range(self.random.randint(minimum, maximum)))
            raise GenerationFailure(f'Unsupported EBNF node: {node.kind}')

        sql = '(' + expand(rule.tree) + ')'
        own_window = 'OVER' in {token.upper() for token in SQL_TOKENS.findall(sql)}
        window = own_window or any(piece.window for piece in pieces)
        aggregate = (rule.aggregate and not own_window) or any(piece.aggregate for piece in pieces)
        free = frozenset(column for piece in pieces for column in piece.free_columns)
        if rule.aggregate:
            if any(piece.aggregate or piece.window for piece in pieces):
                raise GenerationFailure('Aggregate/window calls cannot be aggregate arguments')
            if not own_window:
                free = frozenset()
        ids = (rule.id,) + tuple(rule_id for piece in pieces for rule_id in piece.rule_ids)
        return Expression(sql, rule.return_type, aggregate, ids, free, window)

    def generate(self, target, mode=None):
        mode = mode or self.random.choice(self.MODES)
        table = self.schema[0]
        scope = self.scope(table, 't0')
        source = f'`{table["key"]}` AS `t0`'
        prefix = ''
        if mode == 'join':
            other = self.schema[1]
            scope.columns += self.scope(other, 't1').columns
            source += f' JOIN `{other["key"]}` AS `t1` ON `t0`.`id` = `t1`.`id`'
        elif mode in ('cte', 'derived'):
            if mode == 'cte':
                prefix = f'WITH input_rows AS (SELECT * FROM `{table["key"]}`) '
                source = 'input_rows AS `t0`'
            else:
                source = f'(SELECT * FROM `{table["key"]}`) AS `t0`'
        elif mode in ('scalar_subquery', 'exists'):
            scope = self.scope(self.schema[1], 't1', parent=scope)

        expression = self.expression(target, scope)
        grouping = set(expression.free_columns) if mode == 'group' else set()
        validate_projection([expression], grouping)
        sql = f'{prefix}SELECT {expression.sql} AS result FROM {source}'
        if mode == 'predicate' and not expression.aggregate and not expression.window:
            sql = f'SELECT 1 AS result FROM {source} WHERE {expression.sql} IS NOT NULL'
        elif mode == 'group' and grouping:
            sql += ' GROUP BY ' + ', '.join(sorted(column.sql for column in grouping))
        elif mode == 'order':
            sql += ' ORDER BY result'
        elif mode == 'scalar_subquery':
            sql = f'SELECT (SELECT {expression.sql} FROM `{self.schema[1]["key"]}` AS `t1` LIMIT 1) AS result FROM {source}'
        elif mode == 'exists':
            sql = f'SELECT 1 FROM {source} WHERE EXISTS (SELECT {expression.sql} FROM `{self.schema[1]["key"]}` AS `t1`)'
        elif mode == 'union':
            constant = self.atom(target.return_type, Scope())
            sql += f' UNION ALL SELECT {constant.sql}'
        isolation_source = source
        if mode in ('scalar_subquery', 'exists'):
            isolation_source = (f'`{table["key"]}` AS `t0` JOIN '
                                f'`{self.schema[1]["key"]}` AS `t1` ON `t0`.`id` = `t1`.`id`')
        isolation = f'{prefix}SELECT {expression.sql} AS result FROM {isolation_source} LIMIT 5;'
        return GeneratedSQL(sql + ' LIMIT 5;', expression.rule_ids, isolation)
