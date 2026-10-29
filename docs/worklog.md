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

MySQL training naturally exited with code 0 at 2026-10-29T16:57:47Z:
189/189 corpus entries completed, no failed features, 1,261 retained rules,
and a matching `training_stopped` event. After the writer exited, evidence
import reaudited and checkpointed the numeric-addition replacement and the
two expanded BIT_AND recoveries described above. The resulting snapshot has
1,263 rules. Full training evidence audit is running in
`runs/mysql-final-training-audit`; independent expanded per-rule execution
validation is running in `runs/mysql-final-expanded-validation`. These must
finish successfully before final 10,000-query evaluation and gated export.

The 10,000-query expanded fuzz run started against the same fixed 1,263-rule
snapshot while validation continues (`runs/mysql-final-fuzz10000`). Its first
execution failure, query 404, combines binary left-shift output with the learned
`blobExpr NOT LIKE charAtom` rule (97ee48ed2751d5da867e6fbe), causing MySQL
errno 3854 on binary-to-UTF8 conversion. The exact error was reproduced; casting
the variable pattern to BINARY preserves NOT LIKE and executes successfully.
Replacement 7dc7500f6926d175e92319b9 in `runs/mysql-binary-like-repair-001`
passed 90/90 expanded target executions and independent evidence audit. It has
not been imported while snapshot audits run. After reconciliation, the revised
snapshot requires full validation and a new 10,000-query run; the original
failure and original run must remain retained. Current evidence is provisional.

Expanded revalidation rejected BIT_XOR double-expression rule
61e731e3ab9c28bb597b2ed3 on a nested UUID_SHORT multiplication in aggregate
integer-evaluation context (errno 1690). A UUID_SHORT-side DOUBLE cast candidate
26db5af5c91e5ab9d92edf18 passed random 90-query execution but still failed the
exact retained regression, so `runs/mysql-uuid-short-double-repair-001/decision.json`
explicitly rejects it for import. Decimal conversion at the BIT_XOR input
executes the exact regression successfully; its full expanded trial is running
in `runs/mysql-bitxor-numeric-repair-001` (seed 330000). No new repair has been
imported into the snapshot under audit. Retain this distinction when reconciling.

BIT_XOR replacement 8dd15b6065cc72ce0628374f completed 90/90 expanded
target-confirmed executions and independent audit, in addition to the exact
aggregate regression. Pending imports after the current snapshot experiments:
`runs/mysql-binary-like-repair-001/trial`, replacing 97ee48ed2751d5da867e6fbe
under `String Comparison Functions and Operators::expr NOT LIKE pat [ESCAPE 'escape_char']`;
and `runs/mysql-bitxor-numeric-repair-001/trial`, replacing 61e731e3ab9c28bb597b2ed3
under `Aggregate Function Descriptions::BIT_XOR(expr) [over_clause]`.
Keep original failed snapshot evidence; revised results need new full revalidation,
training evidence audit, and 10,000-query evaluation before export.

Original fuzz query 3430 exposed POWER(0,-2), errno 1690, in integer-operand
POWER rule da37350a06cbba0ed737b068. Candidate 1376c45be39190992249257e
(`runs/mysql-power-domain-repair-001`) guards a zero base with NULLIF but failed
expanded execution on table2.count raised to itself; do not import it.
`runs/mysql-power-domain-repair-002` binds the two original operands once in
a correlated scalar subquery, guards zero-negative powers and log magnitude
outside [-700,700], and preserves variable exponents. Exact database value
checks passed for zero, positive/negative bases, and negative exponents; invalid
and overflow cases return NULL. Its 90-query expanded trial is running.
No POWER replacement has been accepted or imported yet. Original fuzz failures
at indices 404 and 3430 remain included in the execution denominator.

POWER repair-002 failed expanded contextual accuracy (despite zero isolated
target errors): MySQL grouped/HAVING rewrites produced duplicate/unknown column
names in its correlated derived bindings. Do not import it. All of its failed
SQL execute after qualifying `power_args` references and explicitly casting
bound operands to DECIMAL(65,0). Repair-003 in
`runs/mysql-power-domain-repair-003` retains those context regressions and is
currently running the full 90-query validation (seed 0). It is not accepted yet.

POWER repair-003 (9ed59b7460579d5ea02c3f55) subsequently passed 90/90
expanded target executions plus independent evidence audit. Eight explicit
value regressions were rerun using this exact candidate's parsed production;
all matched expected results (including zero/negative-exponent and overflow
guards), and all repair-002 failed contexts execute successfully. It is pending
import under `Mathematical Functions::POWER(X,Y)`, replacing
da37350a06cbba0ed737b068. Only repair-003 is accepted among the POWER attempts.

Parser boundary factoring is now implemented in the working tree: the shared
LP/RP boundary surrounds the ordered learned-rule alternatives once. Named
learnedRule contexts and syntax definitions are retained. A differential test
compares nested aggregate/arithmetic contexts and malformed-input rejection
against the previous dispatcher; the complete suite passed 67 tests. An
independent baseline-versus-factored comparison of all 90 retained MAX trial
SQL is running in runs/parser-parenthesis-factor-benchmark-001. Its first 30
records have identical named-context sets; broader performance conclusions
remain pending. Existing validation/audit/fuzz processes retain their original
loaded runtime; this edit does not retroactively change their evidence. The
three verified replacements above remain pending import, and revised-snapshot
full validation, training audit, and 10,000-query execution remain required.

The retained MAX-trial parser comparison completed all 90 SQL. Every original
and factored parse had identical sets of all named learned-rule contexts,
including nested contexts. Aggregate parsing time was 222.179 seconds for the
original dispatcher and 68.069 seconds for the factored dispatcher (about 3.26x
on this specific retained trial, not a universal performance guarantee).
Raw timings and context sets are retained locally in
runs/parser-parenthesis-factor-benchmark-001/all-comparison.jsonl. Existing
long-running jobs remain on their original loaded runtime and are still live.

The original 1,263-rule expanded fuzz experiment completed naturally with
10,000 retained executions: 9,998 database successes, 2 failures, zero ANTLR
errors, elapsed 2,556.238 seconds. All 10,000 records were independently read
back; the only failures were indices 404 (binary NOT LIKE encoding) and 3430
(POWER zero-negative exponent). This 99.98% result belongs to the unrepaired
snapshot and is not the final deployment result.

To preserve the original live training audit, a separate complete evidence
copy is being reconciled at runs/mysql-reconciled-v2. Its reconciliation.json
records the original snapshot hash and each audited replacement import.
Binary NOT LIKE has been imported; BIT_XOR and POWER imports are proceeding
sequentially. The original runs/mysql source has not been modified. The revised
copy will require its own full revalidation, audit and 10,000-query evaluation.

The audit command now atomically publishes per-rule progress.json containing
current rule, checked/verified/failed counts and final full_run_verified status.
This improves observation of the forthcoming repaired-snapshot audit without
changing acceptance criteria or treating a completed traversal as a passed
audit. The complete test suite passed 67 tests. Existing audit processes keep
their originally loaded implementation. Reconciliation remains live: BIT_XOR
passed its first evidence replay and created an import checkpoint; copied
trial replay is still running before authoritative candidate replacement.

All three verified replacements have now been reconciled into the independent
runs/mysql-reconciled-v2 evidence snapshot. Direct set comparison confirms
exactly the intended three removed IDs and three added IDs, 1,263 rules before
and after, and the original source rules hash remains unchanged. Reconciliation
exited naturally with code 0. Fresh full-snapshot jobs actually launched and
were independently confirmed alive by complete process command lines:
- training audit: runs/mysql-reconciled-v2-training-audit (Python PID 17168);
- expanded per-rule execution validation:
  runs/mysql-reconciled-v2-expanded-validation (Python PID 34344);
- 10,000 expanded SQL execution evaluation:
  runs/mysql-reconciled-v2-fuzz10000 (Python PID 53020).
At first observation: training audit verified 19/1,263 with zero failures,
expanded validation passed its first two rules, and fuzz passed its first 100
executions. These are new snapshot experiments; old counts are not carried
over. See runs/mysql-reconciled-v2/validation-jobs.json and each adjacent .log
for actual handles/output. All final gates and deployment export remain pending.

Repaired-snapshot training audit exposed five false definition mismatches in
historical equality rules: retained EBNF contained duplicate identical sequence
alternatives, while the current compiler deduplicated them. Diagnostic replay
confirmed the error before SQL parsing. normalized_definition now canonicalizes
generated EBNF structure, removing redundant groups and duplicate alternatives
while preserving literal tokens, branch order and repeat quantifiers. Tests
reject changed operators and distinguish optional from mandatory productions;
68 tests passed. All six equality definitions at indices 190-195 compare
equivalent. Recompiling the complete repaired snapshot yields exactly the same
grammar hash as the ongoing fuzz experiment, so generated syntax is unchanged.

The affected audit reader (verified PID 17168) was deliberately stopped for
this confirmed validator defect, its progress marked interrupted with reason,
and its evidence retained. A fresh full audit is running in
runs/mysql-reconciled-v2-training-audit-r2 (exec session 14167). Other snapshot
validation and fuzz processes continue unchanged. Do not use the interrupted
audit as acceptance evidence; the new audit must finish successfully.

The repaired snapshot's training audit has now replayed all formerly
misreported equality rules successfully: 196/1,263 verified, zero failures at
that checkpoint; it subsequently reached 200 verified. The independent static
definition precheck also matched all 1,263 retained target definitions. This
static check does not replace parser-context or database execution evidence.

Original-snapshot audit PID 7628 and revalidation PID 17048 were independently
identified by complete command lines and deliberately stopped as superseded:
their snapshot contains the three confirmed replaced rules and the repaired
snapshot already has independent full acceptance jobs. Original partial
progress and failures remain intact, with explicit superseded.json records;
they cannot certify the repaired snapshot. The active acceptance processes are
training-audit-r2 Python PID 43844 and expanded-validation Python PID 34344.
This cleanup was due to known superseded evidence, not an observation timeout.

A proactive full feature-link/contract precheck found two historical RLIKE
productions linked to expr REGEXP pat. The corpus explicitly says "REGEXP and
RLIKE are synonyms" and documents both spellings in that entry. Treating
RLIKE as removal of the requested operator was a contract false rejection.
Guaranteed-token calculation now canonicalizes that documented operator alias
before alternative intersections. Regression tests still reject missing NOT,
quoted 'RLIKE' values, disappearing branches and REGEXP_LIKE function
substitution for the requested operator syntax. All 73 tests passed.

The metadata precheck now validates all 189 expected/completed/linked features
and every linked rule without contract failures or missing links. Rules and
grammar are unchanged. The r2 audit process (verified PID 43844) retained its
old contract implementation and would falsely reject the two aliases at the
final metadata gate; it was deliberately stopped with an explicit interrupted
reason, preserving progress. Replacement full audit runs at
runs/mysql-reconciled-v2-training-audit-r3 (exec session 58397). Existing
expanded rule validation continues; completed 10,000-query evidence is unchanged.
