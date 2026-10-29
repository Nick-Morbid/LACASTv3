# Running an exported MySQL grammar

The exported directory contains the Python runtime, learned grammar/rules,
schema and type configuration. It requires Python 3.12+, uv, Java 11+, and a
reachable MySQL server. The final delivery manifest records the tested server
version and file hashes. No database password or LLM key is distributed.

1. Copy `.env.example` to `.env` and set the MySQL connection fields. Use a
   dedicated `lacastv3_` database. LLM fields are needed only for further training.
2. Install dependencies and verify the pinned ANTLR tool:

   ```sh
   uv sync
   uv run python scripts/bootstrap.py
   ```

3. On a fresh test database, initialize the two schema tables and check the
   connection with the expanded preflight:

   ```sh
   uv run python scripts/preflight_mysql.py --initialize --expanded --output runs/deployment-preflight
   ```

   Initialization replaces the dedicated test tables. Omit `--initialize` if
   the required schema/data already exists and must be preserved.

4. Execute the exported rules against MySQL:

   ```sh
   uv run python -m lacastv3 fuzz --work-dir . --output runs/fuzz10000 --count 10000
   ```

The output directory must be new. `summary.json` reports database execution
success and ANTLR errors; `sql_results.jsonl` retains every generated SQL and
its outcome. Database failures remain in the denominator. The execution rate
does not compare returned values with a semantic correctness oracle. Testing
against a different server version produces a new result, not the original
delivery's verified accuracy.
