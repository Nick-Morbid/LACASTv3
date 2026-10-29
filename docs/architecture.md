# Architecture and acceptance plan

## Responsibilities

1. **Syntax:** clean ANTLR4 `.g4` files contain syntax only. SQLCraft markers
   such as `&_FROM`, `&_GROUP_BY`, `_var_*`, `_alias`, and `_table` are not
   ANTLR semantic actions. The new base grammar uses ordinary SQL tokens.
2. **Semantics:** Python models SQL types, schemas, visible relations, projection
   aliases, CTEs, subqueries, grouping keys, aggregate placement, and compatible
   set-operation shapes. A generator constructs valid ASTs from that context.
   Semantics must not be enforced by accepting a database error as a valid SQL.
3. **Learned productions:** keep stable rule IDs and typed argument metadata in
   JSON. Compile their syntax to ANTLR rules and retain an exact map from parser
   contexts to rule IDs. Parenthesized expression boundaries avoid indirect
   left recursion when adding learned operators.
4. **Rule coverage:** retain generation derivations AND validate ANTLR parses
   with full-input consumption and no recovered errors. Require the exact
   target rule ID/alternative in both. A textual function-name match is not
   coverage. Discard unrelated statements before database execution and before
   choosing the accuracy denominator. Sampling exhaustion is inconclusive.
5. **Feedback:** execute target-containing SQL against a dedicated MySQL
   database, preserve SQL/errors/target traces, apply the fixed >95% threshold,
   and attribute residual errors before accepting a candidate. Save resumable
   state atomically and never infer completion from a partial batch.

## Work remaining / completion gates

- [x] Clean base syntax compiled by ANTLR4, with lexer/parser error rejection.
- [x] Typed production compiler and exact target-alternative identification.
- [x] Schema-aware generator with CTE/join/subquery/group/set-operation scopes.
      Implemented in the Python generator; scope and composition regressions
      are covered by tests/test_query_semantics.py and tests/test_semantics.py.
- [x] Integrate LLM generation, refinement, persistence, metrics, and CLI.
      The 189-feature training run completed naturally; refinement, evidence
      persistence and CLI paths have regression coverage.
- [x] Reject SQLCraft annotations in new grammar and prompts; no SQLCraft JAR
      or socket server required by the runtime.
- [x] Dedicated MySQL database initialized and its actual version recorded (8.4.11).
- [ ] Retrain every entry of the 189-item MySQL corpus; audit full rule samples.
- [x] Run a 10,000-SQL full-grammar execution evaluation and preserve all errors.
      The repaired 1,263-rule snapshot executed 10,000/10,000 successfully on
      MySQL 8.4.11, with zero ANTLR errors. See
      docs/results/mysql-reconciled-v2-fuzz.json for hashes and evidence paths.
      This sampled result does not replace the pending full rule audit.
- [ ] Document deployment and push the verified project to the requested remote.

Historical training output and hand-written smoke rules cannot substitute for
the new corpus-wide training run. This checklist is intentionally incomplete
until runtime evidence proves each gate.
