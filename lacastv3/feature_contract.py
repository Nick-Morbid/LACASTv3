"""Require the documented feature in every candidate derivation."""
import re

from .compiler import SQL_TOKENS


def guaranteed_tokens(node):
    if node.kind == 'literal':
        # The MySQL corpus explicitly documents REGEXP and RLIKE as synonyms.
        # Normalize before choice intersections so either spelling is guaranteed
        # in every branch; quoted SQL values remain opaque lexer tokens.
        return {'REGEXP' if token.upper() == 'RLIKE' else token.upper()
                for token in SQL_TOKENS.findall(node.value)}
    if node.kind == 'reference':
        return set()
    children = [guaranteed_tokens(child) for child in node.children]
    if node.kind == 'choice':
        return set.intersection(*children) if children else set()
    if node.kind == 'repeat' and node.value != '+':
        return set()
    return set().union(*children)


def validate_feature(feature, rule):
    tokens = guaranteed_tokens(rule.tree)
    if feature.startswith('CASE '):
        if not {'CASE', 'WHEN', 'THEN', 'END'}.issubset(tokens):
            raise ValueError('Candidate removed the requested CASE expression from a derivation')
        return
    function = re.match(r'\s*([A-Za-z_][A-Za-z_0-9]*)\s*\(', feature)
    if function:
        if function[1].upper() not in tokens:
            raise ValueError(f'Candidate removed the requested function {function[1]} from a derivation')
        return
    if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', feature):
        # SQL permits CURRENT_TIME/CURRENT_TIMESTAMP and other special
        # functions without parentheses. Their keyword must still be executed.
        if feature.upper() not in tokens:
            raise ValueError(f'Candidate removed the requested keyword {feature} from a derivation')
        return
    symbol = {'N % M': '%', 'expr LIKE pat [ESCAPE \'escape_char\']': 'LIKE',
              'expr NOT LIKE pat [ESCAPE \'escape_char\']': 'NOT LIKE',
              'expr REGEXP pat': 'REGEXP',
              'expr NOT REGEXP pat': 'NOT REGEXP'}.get(feature, feature)
    contracts = {'IS boolean_value': {'IS'}, 'IS NOT boolean_value': {'IS', 'NOT'},
                 'IS NULL': {'IS', 'NULL'}, 'IS NOT NULL': {'IS', 'NOT', 'NULL'},
                 'NOT LIKE': {'NOT', 'LIKE'},
                 'NOT REGEXP': {'NOT', 'REGEXP'}}
    required = contracts.get(symbol, {symbol})
    supported = {'-', '+', '/', '*', 'DIV', '%', '=', '|', '&', '^', '<<', '>>', '~',
                 'BINARY', '<=>', '<>', '<=', '<', '>=', '>', 'NOT', 'AND', 'OR', 'XOR', 'LIKE', 'REGEXP'}
    if symbol not in supported and symbol not in contracts:
        return
    if not required.issubset(tokens):
        raise ValueError(f'Candidate removed the requested operator {feature} from a derivation')
