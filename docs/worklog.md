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

## Expanded semantic contexts (2026-10-29)

Added typed derived-output bindings, varied projection lists, join variants,
matching set-operation outputs, and alias-safe grouping/HAVING/ORDER contexts.
Window expressions retain argument dependencies and cannot enter WHERE or
same-level HAVING. Training and fuzz CLI now default to `--generation-profile
expanded`; `baseline` remains available for reproducing historical evidence.
Verdicts and fuzz manifests explicitly record that profile. The already-running
training process still uses its original baseline snapshot; its accepted rules
require separate expanded-context revalidation before final delivery.

Verification: 28 unit tests passed; expanded hand-written preflight passed
165/165 queries. A snapshot of actual learned rules was tested in
`runs/mysql-expanded-learned-fuzz-001`: 100/100 MySQL executions passed, zero
ANTLR errors. This diagnostic sample does not replace per-rule revalidation
or the required final 10,000-query run.

Expanded per-rule revalidation is now available through `revalidate`. A
three-rule pilot (`runs/mysql-expanded-revalidation-pilot-001`) passed all
270 target-confirmed executions and independent parser/evidence audits.
The diagnostic limit leaves `full_snapshot_verified=false`. A full snapshot
revalidation was subsequently launched in `runs/mysql-expanded-revalidation-001`
while the original corpus trainer continues; neither writes the other's state.
The snapshot does not include future trainer additions. Unit tests now total 29.

Added gated `export`: requires complete corpus audit, expanded evidence for
the exact exported rule snapshot, and retained 10,000-query fuzz results from
the same server/database. It independently replays rule evidence and compiles
the delivered grammar before writing a delivery manifest. Local credentials
are excluded from copied configurations. Unit tests total 36, including gates
against partial runs, baseline evidence and mismatched snapshots/environments.
No final bundle has been exported: the full runtime gates remain outstanding.

Fixed fuzz provenance under concurrent training: rules are now read exactly
once and retained, so grammar inputs and manifest hashes cannot describe
different trainer revisions. New fuzz/revalidation processes archive an
allowlisted runtime-source ZIP and hash public configurations. Credentials
are excluded. Existing running processes keep their original code snapshots.

Refinement no longer reevaluates an identical candidate already passed in the
same feature and process: it records `rule_evidence_reused` pointing to the
original trial, and continues evaluating new/repaired candidates. It does not
reuse failed candidates or bypass later expanded revalidation. A regression
test exercises a mixed pass/fail response followed by a repair; 38 tests pass.
This change is pending application to the running trainer at its next justified
engine upgrade; its current process still uses the archived baseline code.

Controlled runtime upgrade at 2026-10-29T13:24:54Z: archived state/rules/events
under `runs/mysql/checkpoints/20261029T132454Z`, retained 205 accepted rules and
25 completed features, then resumed using expanded generation. The exclusive
trainer process pair was rechecked; the independent 202-rule snapshot validator
was untouched. The first expanded candidate passed all 90 executions. Runtime
since the last checkpoint for the interrupted feature is explicitly uncounted,
not silently represented as measured elapsed training time.

Candidate feature contracts now require the function/operator token in every
derivation, including alternatives and optional EBNF branches. The independent
audit also checks feature-to-rule contracts. A scan of 210 current accepted
feature/rule links found no missing-feature violations. Unit tests total 47.
The running trainer predates this last guard addition; the final audit enforces
it regardless of which trainer revision accepted a rule.

ANTLR profiling found the validator spending time in recursive prediction over
identical overload syntax: 202 typed rules compiled to just 68 distinct syntax
definitions. The compiler now keeps all named definitions but enters the first
identical production only, preserving target-first alternative resolution.
Against 34 retained real queries and 218 rules, rule-context results were
identical and parse runtime changed from 30.81s to 1.51s. The earlier SLL/LL
experiment was slower and was discarded. Evidence is in
`runs/parser-dedup-benchmark-001/summary.json`.

Revalidation now supports exclusive-lock `--resume`, retaining its immutable
snapshot and completed results, recording runtime attempts, and archiving an
incomplete trial. An interruption/resume regression verifies that later changes
to the source run cannot change the resumed snapshot. Unit tests total 49.

The runtime upgrade was applied at 2026-10-29T13:46:58Z, with a training
checkpoint and validator resume preserving 46 completed results. The fixed
202-rule snapshot validation has now finished: 201 accepted, one rejected
(`4233a4497fca40c8cb0c7cdd`, integerExpr + integerExpr). It failed when a
nested bitwise expression produced BIGINT UNSIGNED and addition overflowed.
`full_snapshot_verified` correctly remains false.

A separate repair experiment (`runs/mysql-expanded-repairs-001`) widens both
integral addition operands to DECIMAL(65,0), preserving variable inputs and
the + operation. Replacement `7fd5677b6619fcb6b2e09085` passed 90/90 expanded
executions plus independent target-context audit. Exact replay reproduced
MySQL error 1690 for the original SQL and succeeded for the repaired SQL,
whose parse includes the replacement target context. Original failure evidence
is retained. The repair is NOT merged into the active trainer; after its writer
exits, replace the rejected rule and its feature mappings/evidence, along with
the two pending recovered BIT_AND rules, then validate the final full snapshot.

Added `import-evidence` for that pending reconciliation. It takes the writer
lock, requires a terminal training record, audits original and copied trial
evidence, checkpoints old rules/mappings/events, validates documented-feature
presence and recompiles before replacing authoritative files. All feature links
referencing a replaced rule are updated. No import has been performed against
the running trainer. Tests include active-writer rejection and replacement/link
checkpointing; 54 tests pass.

Diagnostic expanded fuzz of the live learned-rule snapshot completed in
`runs/mysql-expanded-diagnostic-fuzz1000-001`: 1,000/1,000 actual MySQL 8.4.11
executions succeeded, zero ANTLR errors, 107.73 seconds. Every generated SQL
was retained and executed, with no target filtering or failure resampling.
This is an intermediate 1,000-query diagnostic, not the final 10,000-query
evaluation and not evidence overturning the known overflow rejection.

Further removed duplicate operand alternatives inside a production (typed
overloads can otherwise emit `(expression | expression)`). Historical trial
audit normalizes only redundant bare-expression groups and leaves quoted SQL
literals and real operator differences untouched. A real historical trial
(`413076db57ff346764288880`) reaudited successfully. On 389 learned rules and
20 retained SQL, parser contexts matched exactly and parse runtime changed
from 6.70s to 2.14s (`runs/compiler-choice-benchmark-001`). Tests total 55.

Feature-presence auditing also covers bare-keyword functions such as
CURRENT_TIME and CURRENT_TIMESTAMP, including every optional/alternative
derivation. A scan of the current 459 accepted feature/rule links found no
violations. Tests total 58. Training continues normally; this additional guard
will be enforced by the final independent audit without restarting the trainer.

Deployment assets now include public prompt files, initialization/preflight
scripts, `.env.example`, documentation and an explicit config allowlist. Runtime
provenance archives include prompts and scripts as well. A regression boots the
copied CLI from an independent directory without local credentials. Tests: 59.

Standalone smoke in `runs/mysql-deployment-assets-smoke-001` confirmed its
runtime ROOT is the copied directory, downloaded and checksum-verified ANTLR,
and executed 20/20 generated SQL on MySQL with zero parser errors. It used an
explicit external connection config without copying it. This is a deployment
asset smoke only; the final evidence-gated export has not yet been produced.

The two pending BIT_AND recoveries were rechecked under expanded generation
against a newer learned-rule snapshot in `runs/mysql-expanded-bitand-recovery-001`.
Both `253317da1f5f2713937d4d14` and `c31ef89ffe36eb0338a28b36` passed 90/90
target-confirmed executions plus independent audits (180/180 in total). Use
these expanded `trial-<rule_id>` directories for the pending post-writer
imports, rather than the earlier baseline recovery evidence. Nothing was
imported into the active trainer.

Compound CASE documentation signatures now require CASE/WHEN/THEN/END in
every candidate derivation, rather than falling outside function/operator
keyword checks. All eight already accepted CASE rules pass the new contract.
The final independent audit enforces it; no trainer restart is needed. Tests: 61.

The remaining regex operator signatures `expr REGEXP pat` and `expr NOT REGEXP pat`
now require their operator tokens in every derivation. Regression tests reject
replacement by REGEXP_LIKE, omission of NOT, and alternatives that omit REGEXP.
The active trainer continues unchanged; final independent auditing uses these
contracts before delivery. Tests: 66 passed. Training last confirmed at 167/189
with no failed features; this is not a completion claim.
