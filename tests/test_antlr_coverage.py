from pathlib import Path

import pytest

from lacastv3.compiler import compile_rules, normalized_definition, terminal
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
        Rule('epsilon', 'double', 'doubleAtom "+ 1e-6"'),
        Rule('add-int', 'integer', 'integerAtom "+" integerAtom'),
        Rule('round-int', 'double', '"ROUND(" doubleAtom ", 1)"'),
        Rule('date-format', 'text', '"DATE_FORMAT(" dateAtom ", \'%Y\')"'),
        Rule('pad-bit', 'blob', '"BIT_AND(RPAD(" blobAtom ", 1, 0x00))"', True),
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
    assert parser.parse("SELECT CAST('abc' AS CHAR(1)), 0x00, 0b1, .5 LIMIT 1;")
    assert 'pad-bit' in parser.parse("SELECT (BIT_AND(RPAD(X'61', 1, 0x00))) FROM table1;").rule_ids
    assert 'epsilon' in parser.parse('SELECT (1.5 + 1e-6);').rule_ids


def test_sqlcraft_annotations_are_rejected():
    with pytest.raises(ValueError):
        parse_production('"SELECT" expression&_FROM')


def test_duplicate_syntax_keeps_first_target_context_and_all_definitions(tmp_path):
    rules = [Rule('target-double', 'double', '"ABS(" doubleAtom ")"'),
             Rule('alias-int', 'integer', '"ABS(" integerAtom ")"')]
    grammar = tmp_path / 'LearnedMySQL.g4'
    mapping = compile_rules(ROOT / 'configs/mysql/MySQLBase.g4', rules, grammar)
    source = grammar.read_text()
    assert 'learnedPrimary: LP (learnedRule0) RP;' in source
    assert 'learnedRule1:' in source
    syntax = SQLParser(grammar, ROOT / 'vendor/antlr-4.13.2-complete.jar', tmp_path / 'cache', mapping)
    assert syntax.parse('SELECT (ABS(1));').rule_ids == {'target-double'}
    # Reordering for a different candidate makes that candidate reachable first.
    mapping = compile_rules(ROOT / 'configs/mysql/MySQLBase.g4', list(reversed(rules)), grammar)
    syntax = SQLParser(grammar, ROOT / 'vendor/antlr-4.13.2-complete.jar', tmp_path / 'cache', mapping)
    assert syntax.parse('SELECT (ABS(1));').rule_ids == {'alias-int'}


def test_definition_normalization_only_removes_redundant_operand_choices():
    old = "learnedRule0: (expression | expression) '+' expression;"
    new = "learnedRule0: expression '+' expression;"
    assert normalized_definition(old) == normalized_definition(new)
    literal = 'learnedRule0: ' + terminal("'(expression | expression)'") + ';'
    assert normalized_definition(literal) != normalized_definition(
        literal.replace('(expression | expression)', 'expression'))
    assert normalized_definition(old) != normalized_definition(new.replace("'+'", "'-'"))


def test_normalization_collapses_duplicate_sequences_but_preserves_alternatives():
    simple = "learnedRule0: expression '=' expression;"
    duplicated = "learnedRule0: (expression '=' expression | expression '=' expression);"
    assert normalized_definition(simple) == normalized_definition(duplicated)
    assert normalized_definition(simple) != normalized_definition(duplicated.replace("'='", "'<>'", 1))
    optional = "learnedRule0: (expression '=' expression)?;"
    assert normalized_definition(simple) != normalized_definition(optional)
    assert normalized_definition(optional) == normalized_definition(
        "learnedRule0: ((expression '=' expression | expression '=' expression))?;")


def test_factored_boundaries_preserve_nested_contexts_and_rejection(tmp_path):
    rules = [Rule('abs', 'integer', '"ABS(" integerExpr ")"'),
             Rule('add', 'integer', 'integerExpr "+" integerExpr'),
             Rule('max', 'double', '"MAX(" ("DISTINCT ")? doubleExpr ")"', True)]
    grammar = tmp_path / 'FactoredMySQL.g4'
    mapping = compile_rules(ROOT / 'configs/mysql/MySQLBase.g4', rules, grammar)
    baseline = tmp_path / 'OriginalMySQL.g4'
    source = grammar.read_text().replace('grammar FactoredMySQL;', 'grammar OriginalMySQL;')
    source = source.replace('learnedPrimary: LP (learnedRule0 | learnedRule1 | learnedRule2) RP;',
                            'learnedPrimary: LP learnedRule0 RP | LP learnedRule1 RP | LP learnedRule2 RP;')
    baseline.write_text(source)
    jar = ROOT / 'vendor/antlr-4.13.2-complete.jar'
    old = SQLParser(baseline, jar, tmp_path / 'old', mapping)
    new = SQLParser(grammar, jar, tmp_path / 'new', mapping)
    for sql, expected in [
        ('SELECT (ABS((2 + 3)));', {'abs', 'add'}),
        ('SELECT (MAX(DISTINCT (ABS(2)))) FROM table1;', {'max', 'abs'}),
        ('SELECT ((ABS(2)) + (ABS(3)));', {'add', 'abs'}),
        ('SELECT ABS(2);', set()),
    ]:
        assert old.parse(sql).rule_ids == new.parse(sql).rule_ids == expected
    for sql in ['SELECT (ABS(2);', 'SELECT ((2 + 3)); garbage']:
        for parser in (old, new):
            with pytest.raises(ParseFailure):
                parser.parse(sql)


def test_productions_cannot_smuggle_another_statement(tmp_path):
    with pytest.raises(ValueError, match='separator'):
        compile_rules(ROOT / 'configs/mysql/MySQLBase.g4',
                      [Rule('invalid', 'integer', '"1; DELETE FROM table1"')],
                      tmp_path / 'Unsafe.g4')
