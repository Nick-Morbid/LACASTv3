"""A small EBNF for learned expressions; SQL semantics live outside .g4 files."""
from dataclasses import dataclass
import json
import re


@dataclass(frozen=True)
class Node:
    kind: str
    value: str = ""
    children: tuple = ()


TOKEN = re.compile(r'\s*("(?:\\.|[^"\\])*"|[a-zA-Z_][a-zA-Z_0-9]*|[()|?*+])')


def parse_production(source: str) -> Node:
    tokens = []
    pos = 0
    while source[pos:].strip():
        match = TOKEN.match(source, pos)
        if not match:
            raise ValueError(f"Unsupported production syntax at {source[pos:pos+30]!r}")
        tokens.append(match[1])
        pos = match.end()
    index = 0

    def alternatives():
        nonlocal index
        choices = [sequence()]
        while index < len(tokens) and tokens[index] == '|':
            index += 1
            choices.append(sequence())
        return choices[0] if len(choices) == 1 else Node('choice', children=tuple(choices))

    def sequence():
        nonlocal index
        nodes = []
        while index < len(tokens) and tokens[index] not in ('|', ')'):
            token = tokens[index]
            index += 1
            if token == '(':
                node = alternatives()
                if index >= len(tokens) or tokens[index] != ')':
                    raise ValueError('Unclosed EBNF group')
                index += 1
            elif token.startswith('"'):
                node = Node('literal', json.loads(token))
            elif re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9]*', token):
                node = Node('reference', token)
            else:
                raise ValueError(f'Unexpected EBNF token: {token}')
            if index < len(tokens) and tokens[index] in ('?', '*', '+'):
                node = Node('repeat', tokens[index], (node,))
                index += 1
            nodes.append(node)
        return Node('sequence', children=tuple(nodes))

    result = alternatives()
    if index != len(tokens):
        raise ValueError('Unexpected closing group')
    return result


@dataclass(frozen=True)
class Rule:
    id: str
    return_type: str
    production: str
    aggregate: bool = False

    @property
    def tree(self):
        return parse_production(self.production)
