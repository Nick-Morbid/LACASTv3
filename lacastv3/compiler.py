"""Compile learned syntax into actual ANTLR contexts with stable coverage IDs."""
from pathlib import Path
import re

from .productions import Rule


SQL_TOKENS = re.compile(r"'(?:''|\\.|[^'\\])*'|`(?:``|[^`])*`|[a-zA-Z_][a-zA-Z_0-9$]*|[0-9]+(?:\.[0-9]+)?|<=>|<>|!=|<=|>=|<<|>>|&&|\|\||[^\s]")


def terminal(text):
    return "'" + text.replace('\\', '\\\\').replace("'", "\\'") + "'"


def compile_rules(base: Path, rules: list[Rule], destination: Path):
    if len({rule.id for rule in rules}) != len(rules):
        raise ValueError('Duplicate rule IDs')
    rule_map = {f'learnedRule{i}': rule.id for i, rule in enumerate(rules)}
    literal_tokens = set()

    def emit(node):
        if node.kind == 'literal':
            tokens = SQL_TOKENS.findall(node.value)
            if ';' in tokens:
                raise ValueError('An expression production cannot contain a SQL statement separator')
            literal_tokens.update(tokens)
            return ' '.join(terminal(token) for token in tokens)
        if node.kind == 'reference':
            # Type information belongs to the generator. Syntax intentionally
            # accepts general expressions; semantic checking is a separate pass.
            if not re.fullmatch(r'(?:[a-z]+(?:Atom|Expr)|anyAtom)', node.value):
                raise ValueError(f'Unknown typed operand: {node.value}')
            return 'expression'
        if node.kind == 'sequence':
            return ' '.join(emit(child) for child in node.children)
        if node.kind == 'choice':
            return '(' + ' | '.join(emit(child) for child in node.children) + ')'
        if node.kind == 'repeat':
            return '(' + emit(node.children[0]) + ')' + node.value
        raise ValueError(node.kind)

    source = base.read_text(encoding='utf-8')
    if rules:
        source = source.replace('primary\n    : literal', 'primary\n    : learnedPrimary\n    | literal')
        source += '\nlearnedPrimary: ' + ' | '.join(f"LP {name} RP" for name in rule_map) + ';\n'
        for name, rule in zip(rule_map, rules):
            source += f'{name}: {emit(rule.tree)};\n'
        # Implicit ANTLR literals take lexical precedence over IDENTIFIER,
        # INTEGER and STRING. Preserve those tokens in generic SQL contexts too.
        base_keywords = set(re.findall(r"'([A-Z][A-Z_]*)'", base.read_text(encoding='utf-8')))
        words = sorted(token for token in literal_tokens
                       if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', token)
                       and token.upper() not in base_keywords)
        values = sorted(token for token in literal_tokens
                        if token.startswith(("'", '`')) or re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', token))
        integers = sorted(token for token in literal_tokens if re.fullmatch(r'[0-9]+', token))
        if words:
            source = source.replace('identifier: IDENTIFIER | QUOTED_IDENTIFIER;',
                'identifier: IDENTIFIER | QUOTED_IDENTIFIER | ' + ' | '.join(map(terminal, words)) + ';')
        if values:
            source = source.replace("| 'FALSE';", "| 'FALSE' | " + ' | '.join(map(terminal, values)) + ';')
        if integers:
            source = source.replace('limitClause: \'LIMIT\' INTEGER (\'OFFSET\' INTEGER | COMMA INTEGER)?;',
                "limitClause: 'LIMIT' integerLiteral ('OFFSET' integerLiteral | COMMA integerLiteral)?;")
            source += 'integerLiteral: INTEGER | ' + ' | '.join(map(terminal, integers)) + ';\n'
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.stem != base.stem:
        source = source.replace(f'grammar {base.stem};', f'grammar {destination.stem};', 1)
    destination.write_text(source, encoding='utf-8')
    return rule_map
