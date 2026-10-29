"""Compile learned syntax into actual ANTLR contexts with stable coverage IDs."""
from pathlib import Path
import re

from .productions import Rule


SQL_TOKENS = re.compile(
    r"[bBxX]'(?:''|\\.|[^'\\])*'|0[xX][0-9a-fA-F]+|0[bB][01]+|"
    r"'(?:''|\\.|[^'\\])*'|`(?:``|[^`])*`|"
    r"(?:[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+)(?:[eE][+-]?[0-9]+)?|"
    r"[a-zA-Z_][a-zA-Z_0-9$]*|<=>|->>|->|:=|<>|!=|<=|>=|<<|>>|&&|\|\||[^\s]"
)
SQL_VALUE = re.compile(
    r"(?:[bBxX])?'(?:''|\\.|[^'\\])*'|0[xX][0-9a-fA-F]+|0[bB][01]+|"
    r"(?:[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+)(?:[eE][+-]?[0-9]+)?"
)


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
        definitions = [emit(rule.tree) for rule in rules]
        # Typed overloads often compile to identical syntax. Keep every named
        # definition for provenance, but enter only the first identical one.
        # Training puts the candidate first, so learnedRule0 remains reachable.
        # This preserves first-alternative resolution without exploring dozens
        # of indistinguishable recursive alternatives at every expression.
        seen = set()
        active_names = []
        for name, definition in zip(rule_map, definitions):
            if definition not in seen:
                active_names.append(name)
                seen.add(definition)
        source = source.replace('primary\n    : literal', 'primary\n    : learnedPrimary\n    | literal')
        source += '\nlearnedPrimary: ' + ' | '.join(f"LP {name} RP" for name in active_names) + ';\n'
        for name, definition in zip(rule_map, definitions):
            source += f'{name}: {definition};\n'
        # Implicit ANTLR literals take lexical precedence over IDENTIFIER,
        # INTEGER and STRING. Preserve those tokens in generic SQL contexts too.
        base_keywords = set(re.findall(r"'([A-Z][A-Z_]*)'", base.read_text(encoding='utf-8')))
        words = sorted(token for token in literal_tokens
                       if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', token)
                       and token.upper() not in base_keywords)
        values = sorted(token for token in literal_tokens if SQL_VALUE.fullmatch(token))
        integers = sorted(token for token in literal_tokens if re.fullmatch(r'[0-9]+', token))
        if words:
            source = source.replace('identifier: IDENTIFIER | QUOTED_IDENTIFIER;',
                'identifier: IDENTIFIER | QUOTED_IDENTIFIER | ' + ' | '.join(map(terminal, words)) + ';')
        if values:
            source = source.replace("| 'FALSE';", "| 'FALSE' | " + ' | '.join(map(terminal, values)) + ';')
        if integers:
            parser_section, lexer_section = source.split('\nLP:', 1)
            parser_section = re.sub(r'\bINTEGER\b', 'integerLiteral', parser_section)
            source = parser_section + '\nLP:' + lexer_section
            source += 'integerLiteral: INTEGER | ' + ' | '.join(map(terminal, integers)) + ';\n'
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.stem != base.stem:
        source = source.replace(f'grammar {base.stem};', f'grammar {destination.stem};', 1)
    destination.write_text(source, encoding='utf-8')
    return rule_map
