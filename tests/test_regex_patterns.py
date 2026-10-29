import random

from lacastv3.generator import SQLGenerator
from lacastv3.productions import Rule
from lacastv3.regex_patterns import mysql_string, regex_pattern
from lacastv3.semantics import Scope


def test_pattern_composition_is_varied_and_reproducible():
    a, b = random.Random(71), random.Random(71)
    patterns = [regex_pattern(a) for _ in range(200)]
    assert patterns == [regex_pattern(b) for _ in range(200)]
    assert len(set(patterns)) > 150
    assert all(pattern for pattern in patterns)
    assert any('|' in pattern for pattern in patterns)
    assert any('{1,3}' in pattern for pattern in patterns)


def test_regex_operand_preserves_target_and_sql_string_escaping():
    assert mysql_string("a'b\\.") == "'a''b\\\\.'"
    rule = Rule('regex', 'integer', 'charAtom " REGEXP " regexpatternAtom')
    generator = SQLGenerator([], {'char': ["'subject'"]}, [rule])
    expression = generator.expression(rule, Scope())
    assert expression.rule_ids == ('regex',)
    assert expression.datatype == 'integer'
    assert ' REGEXP ' in expression.sql
