"""Compile ANTLR grammars and reject lexer/parser recovery as validation."""
from dataclasses import dataclass
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import shutil

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener


class ParseFailure(ValueError):
    pass


class Errors(ErrorListener):
    def __init__(self):
        self.messages = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.messages.append(f"{line}:{column}: {msg}")


@dataclass
class ParsedSQL:
    sql: str
    tree: object
    parser: object
    rule_ids: frozenset[str]


class SQLParser:
    def __init__(self, grammar: Path, antlr_jar: Path, cache: Path,
                 rule_map: dict[str, str] | None = None):
        self.rule_map = rule_map or {}
        digest = hashlib.sha256(grammar.read_bytes() + antlr_jar.read_bytes()).hexdigest()
        self.directory = cache / digest
        self.directory.mkdir(parents=True, exist_ok=True)
        name = grammar.stem
        parser_path = self.directory / f"{name}Parser.py"
        if not parser_path.exists():
            java = shutil.which('java')
            if not java:
                raise RuntimeError('Java runtime is required to compile ANTLR4 grammars')
            subprocess.run([
                java, "-jar", str(antlr_jar.resolve()), "-Dlanguage=Python3",
                "-o", str(self.directory.resolve()), str(grammar.resolve()),
            ], check=True, capture_output=True, text=True)
        self.lexer_class = self._load(self.directory / f"{name}Lexer.py", digest + "lexer", name + "Lexer")
        self.parser_class = self._load(parser_path, digest + "parser", name + "Parser")

    @staticmethod
    def _load(path, module_name, class_name):
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, class_name)

    def parse(self, sql: str) -> ParsedSQL:
        errors = Errors()
        lexer = self.lexer_class(InputStream(sql))
        lexer.removeErrorListeners()
        lexer.addErrorListener(errors)
        tokens = CommonTokenStream(lexer)
        parser = self.parser_class(tokens)
        parser.removeErrorListeners()
        parser.addErrorListener(errors)
        tree = parser.query()
        tokens.fill()
        if errors.messages:
            raise ParseFailure("; ".join(errors.messages))
        found = set()
        stack = [tree]
        while stack:
            node = stack.pop()
            if hasattr(node, "getRuleIndex"):
                name = parser.ruleNames[node.getRuleIndex()]
                if name in self.rule_map:
                    found.add(self.rule_map[name])
            stack.extend(getattr(node, "children", None) or [])
        return ParsedSQL(sql, tree, parser, frozenset(found))
