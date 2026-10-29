"""The accuracy denominator contains only independently confirmed target SQL."""
from dataclasses import dataclass

from .parser import ParseFailure, SQLParser


@dataclass(frozen=True)
class GeneratedSQL:
    sql: str
    derivation: tuple[str, ...]
    isolation_sql: str | None = None


def target_samples(candidates: list[GeneratedSQL], target_id: str,
                   parser: SQLParser) -> list[GeneratedSQL]:
    accepted = []
    for candidate in candidates:
        if target_id not in candidate.derivation:
            continue
        try:
            parsed = parser.parse(candidate.sql)
        except ParseFailure:
            continue
        if target_id in parsed.rule_ids:
            accepted.append(candidate)
    return accepted
