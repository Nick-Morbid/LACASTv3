# Refactor evidence and remaining work

2026-10-29: new repository initialized and pushed to the requested GitHub origin.
Runtime uses ANTLR 4.13.2 and a Python generator, with no SQLCraft JAR dependency.
MySQL is an existing 8.4.11 server; all initialization and retraining use the
separate `lacastv3_mysql` database. Credentials remain in ignored local files.

## Verified evidence

- Clean MySQL base grammar compiles with ANTLR and rejects lexer/parser errors.
- Target SQL needs both its generation rule ID and exact ANTLR rule context.
- Domain/data errors, unrelated SQL, incomplete samples, replaced productions,
  and missing isolated-error evidence cannot produce a successful evidence audit.
- All 189 corpus entries have distinct category/signature keys. Two duplicate
  signature names (`=` and `FORMAT(X,D)`) no longer collapse entries.
- MySQL preflight: 100/100 executions across ten SQL contexts.
- Real AVG pilot: six rules; retained execution evidence independently audited.
- During full training, an intermediate audit verified 128/128 retained rules,
  including all three batches per rule. This was a partial audit, not completion.
- Hexadecimal/scientific literals preserve token boundaries. Two initially
  inconclusive BIT_AND rules were rechecked after the compiler correction;
  both passed 90/90 executions in `runs/mysql-sampling-recheck-001`.

## Active run and pending gates

The full run is `runs/mysql`. Its exclusive file lock prevents another trainer
from writing the same directory. Each engine revision used by this run is
archived there, and code-change restarts are recorded in `events.jsonl`.

- Complete the 189-entry run and inspect any remaining failed features.
- After its writer exits, merge the two recovered BIT_AND rules together with
  their retained evidence and feature mappings; do not edit the live rule file.
- Complete semantic-generation parity, including varied projection lists and
  derived output-column typing, and verify learned rules under that context.
- Run a complete evidence audit and the 10,000-query execution evaluation.
- Publish the final deployable grammar/rules and metrics with source hashes.

These gates remain open; initial tests and intermediate metrics are not the
final retraining result.
