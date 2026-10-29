"""End-to-end smoke verification; these hand-written rules are not training."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from lacastv3.compiler import compile_rules
from lacastv3.coverage import target_samples
from lacastv3.database import MySQLDatabase
from lacastv3.generator import SQLGenerator
from lacastv3.parser import SQLParser
from lacastv3.productions import Rule

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--db-config', type=Path)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--initialize', action='store_true')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
db = MySQLDatabase(config_file=args.db_config)
if args.initialize:
    db.initialize(ROOT / 'configs/mysql/schema.sql')
rules = [Rule('preflight-abs', 'integer', '"ABS(" integerAtom ")"'),
         Rule('preflight-sum', 'double', '"SUM(" doubleAtom ")"', True)]
grammar = args.output / 'PreflightMySQL.g4'
mapping = compile_rules(ROOT / 'configs/mysql/MySQLBase.g4', rules, grammar)
syntax = SQLParser(grammar, ROOT / 'vendor/antlr-4.13.2-complete.jar', args.output / 'parser', mapping)
generator = SQLGenerator(
    json.loads((ROOT / 'configs/mysql/schema.json').read_text()),
    json.loads((ROOT / 'configs/mysql/semantics.json').read_text())['types'], rules,
)
conn = db.connect()
results = []
try:
    with conn.cursor() as cursor:
        cursor.execute('SELECT VERSION(), DATABASE(), @@sql_mode')
        version, database, mode = cursor.fetchone()
    for rule in rules:
        for shape in generator.MODES:
            for _ in range(5):
                candidate = generator.generate(rule, shape)
                retained = target_samples([candidate], rule.id, syntax)
                if not retained:
                    raise RuntimeError(f'ANTLR target coverage missing in {shape}: {candidate.sql}')
                result = db.execute(conn, candidate.sql)
                results.append({'rule_id': rule.id, 'shape': shape, 'sql': candidate.sql, **result})
finally:
    conn.close()
summary = {'status': 'passed' if all(item['ok'] for item in results) else 'failed',
           'server_version': version, 'database': database, 'sql_mode': mode,
           'queries': len(results), 'passed': sum(item['ok'] for item in results),
           'scope': 'Hand-written infrastructure smoke rules only; not corpus training.'}
(args.output / 'sql_results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
(args.output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary['status'] == 'passed' else 1)
