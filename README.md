# LACASTv3

SQL grammar learning with ANTLR4 parsing, a schema-aware Python SQL generator,
and execution feedback from the target database.

## Refactor status

Implementation is in progress. The MySQL corpus and schema are inherited from
the SPARC-SQL space expander; no previously trained rules count as v3 training.

ANTLR4 parses generated SQL. A separate generator owns type, scope, aggregation,
and derivation metadata. Training measures only SQL whose derivation contains
the exact candidate rule and whose ANTLR parse confirms that production. Empty
or incomplete target samples never count as successful training.

See `docs/architecture.md` for the implementation and acceptance requirements.

## Development setup

Requires Python 3.12+, `uv`, and Java 11+ for the ANTLR tool.

```sh
uv sync --extra test
uv run python scripts/bootstrap.py
uv run pytest -q
```

Copy `.env.example` to `.env` and configure an OpenAI-compatible LLM endpoint
and a MySQL connection. The dedicated database is `lacastv3_mysql`. Initialize
only that database with the smoke preflight, then start corpus-wide training:

```sh
uv run python scripts/preflight_mysql.py --initialize --output runs/preflight
uv run python -m lacastv3 train --dbms mysql --work-dir runs/mysql
uv run python -m lacastv3 audit --work-dir runs/mysql --output runs/mysql-audit
uv run python -m lacastv3 fuzz --dbms mysql --work-dir runs/mysql --output runs/mysql-fuzz10000 --count 10000
```

The smoke preflight creates the dedicated database and its two test tables.
Do not run `--initialize` against a database whose test data you want to retain.
The trainer resumes the same work directory and takes an exclusive file lock
to prevent concurrent writers. `--feature-limit` is for diagnosis only; omit it
for the complete 189-entry MySQL corpus. Training retains three batches of 30
target-confirmed SQL statements per candidate and writes the SQL, derivation,
execution errors and isolated-error attribution for audit.

The current initial end-to-end preflight ran 100/100 SQL successfully against
MySQL 8.4.11 with ONLY_FULL_GROUP_BY enabled. One real documentation-based AVG
pilot completed with six accepted rules; this is not the full retraining result.

The fuzz command executes every generated query, retains all database failures,
and reports ANTLR parsing errors separately. Its output directory must be new.
The execution-success rate does not verify the returned SQL result values.

The audit command replays ANTLR parsing for each retained execution sample,
checks the exact stored production, and recomputes all three 30-query acceptance
batches. A complete audit also requires all 189 category/signature corpus entries
and a terminal completion record. `--allow-partial` can inspect an ongoing run
without claiming completion. Duplicate signatures in different documentation
categories have separate corpus identities.

Training and fuzzing default to the `expanded` generation profile, including
typed derived outputs, varied projections, joins, set operations and HAVING.
Use `--generation-profile baseline` only to reproduce older generator evidence.
Profiles are recorded in execution manifests and candidate verdicts. An existing
Python training process keeps its originally loaded generator until restarted.

To independently recheck a fixed snapshot of learned rules under expanded
contexts without modifying the source run:

```sh
uv run python -m lacastv3 revalidate --work-dir runs/mysql --output runs/mysql-expanded-validation
```

This performs three batches of 30 target-confirmed executions per rule and
independently audits retained parser/execution evidence. Failures are retained
in `summary.json`; `full_snapshot_verified` is true only if every snapshot rule
passes. `--rule-limit` is diagnostic and cannot certify an untested remainder.
A snapshot of an ongoing run does not certify subsequently accepted rules or
the completion of the original training corpus.

An interrupted revalidation can resume the same output directory with
`--resume`. It keeps the original immutable rule snapshot even if the source
training run has grown, preserves completed results, and archives any incomplete
trial before retrying it. A per-directory lock prevents concurrent validators.

After full training, expanded revalidation and the 10,000-query fuzz run finish,
create a deployment directory with:

```sh
uv run python -m lacastv3 export --work-dir runs/mysql --validation-dir runs/mysql-expanded-validation --fuzz-dir runs/mysql-fuzz10000 --output runs/mysql-delivery
```

Export replays the full training audit and each expanded trial audit, checks
identical rule/grammar hashes and retained fuzz counts, and includes runtime
code, clean grammar, type/schema configuration, bootstrap script and hashes.
Local credentials are excluded. The delivery manifest is written only after
all gates pass. Fuzz execution accuracy remains a measured result, not an
assertion that every returned value is semantically correct.

After the trainer has stopped, independently verified repairs can be imported:

```sh
uv run python -m lacastv3 import-evidence --work-dir runs/mysql --trial runs/mysql-expanded-repairs-001/trial --feature-key "Arithmetic Operators::+" --replace-rule 4233a4497fca40c8cb0c7cdd
```

The import holds the training-directory lock, requires a terminal training
record, replays the trial audit, backs up prior rules and mappings, and updates
all affected feature links. Omit `--replace-rule` to add a recovered candidate.
Import does not replace final full-snapshot revalidation and fuzzing.
