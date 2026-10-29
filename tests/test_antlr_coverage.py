from pathlib import Path

import pytest

from lacastv3.compiler import compile_rules
from lacastv3.coverage import GeneratedSQL, target_samples
from lacastv3.parser import SQLParser, ParseFailure
from lacastv3.productions import Rule, parse_production

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def parser(tmp_path_factory):
    directory = tmp_path_factory.mktemp('parser')
    grammar = directory / 'LearnedMySQL.g4'
    mapping = compile_rules(ROOT / 'configs/mysql/MySQLBase.g4', [
        Rule('abs-int', 'integer', '"ABS(" integerAtom ")"'),
        Rule('add-int', 'integer', 'integerAtom "+" integerAtom'),
        Rule('round-int', 'double', '"ROUND(" doubleAtom ", 1)"'),
        Rule('date-format', 'text', '"DATE_FORMAT(" dateAtom ", \'%Y\')"'),
    ], grammar)
    return SQLParser(grammar, ROOT / 'vendor/antlr-4.13.2-complete.jar',
                     directory / 'cache', mapping)


def test_exact_rule_context_is_recorded(parser):
    result = parser.parse('SELECT (ABS(-2));')
    assert result.rule_ids == {'abs-int'}
    assert parser.parse('SELECT (2 + 3);').rule_ids == {'add-int'}


def test_unrelated_and_false_provenance_are_filtered(parser):
    samples = [GeneratedSQL('SELECT 1;', ()),
               GeneratedSQL('SELECT 2;', ('abs-int',)),
               GeneratedSQL('SELECT (ABS(-2));', ()),
               GeneratedSQL('SELECT (ABS(-2));', ('abs-int',))]
    assert target_samples(samples, 'abs-int', parser) == [samples[-1]]


@pytest.mark.parametrize('sql', ['SELECT (ABS(2)); garbage', 'SELECT @;', 'SELECT (ABS(2);'])
def test_parser_recovery_cannot_count_as_success(parser, sql):
    with pytest.raises(ParseFailure):
        parser.parse(sql)


def test_wrong_arity_is_not_target_coverage(parser):
    # Generic SQL function syntax is legal; exact learned-rule arity is not.
    assert 'abs-int' not in parser.parse('SELECT (ABS());').rule_ids
    assert not target_samples([GeneratedSQL('SELECT (ABS());', ('abs-int',))], 'abs-int', parser)


def test_nested_target_is_detected(parser):
    assert 'abs-int' in parser.parse('SELECT ((ABS(-2)) + 4);').rule_ids


def test_fixed_literals_do_not_break_generic_tokens(parser):
    assert 'round-int' in parser.parse('SELECT (ROUND(1, 1)) LIMIT 1;').rule_ids
    assert parser.parse("SELECT '%Y', 1 LIMIT 1;")
    assert 'date-format' in parser.parse("SELECT (DATE_FORMAT(CAST('2024-01-01' AS DATE), '%Y'));").rule_ids


def test_sqlcraft_annotations_are_rejected():
    with pytest.raises(ValueError):
        parse_production('"SELECT" expression&_FROM')
