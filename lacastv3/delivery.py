"""Gate deployment exports on complete training, revalidation and fuzz evidence."""
import hashlib
import json
from pathlib import Path
import shutil

from .audit import run_audit, verify_trial
from .compiler import compile_rules
from .productions import Rule
from .training import ROOT, save


def copy_runtime_assets(output: Path):
    """Copy public setup/runtime inputs explicitly, never local credentials."""
    for name in ('README.md', 'DEPLOYMENT.md', 'pyproject.toml', 'uv.lock', '.env.example', '.gitignore'):
        shutil.copy2(ROOT / name, output / name)
    shutil.copytree(ROOT / 'lacastv3', output / 'lacastv3', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    config = output / 'configs/mysql'
    config.mkdir(parents=True)
    for name in ('MySQLBase.g4', 'schema.json', 'schema.sql', 'semantics.json', 'web_corpus.json'):
        shutil.copy2(ROOT / 'configs/mysql' / name, config / name)
    for folder, pattern in (('scripts', '*.py'), ('prompts', '*.txt'), ('docs', '*.md')):
        (output / folder).mkdir()
        for path in (ROOT / folder).glob(pattern):
            shutil.copy2(path, output / folder / path.name)


def check_evaluation(rules_bytes, validation_manifest, validation, fuzz_manifest, fuzz):
    digest = hashlib.sha256(rules_bytes).hexdigest()
    rules = json.loads(rules_bytes)
    ids = {rule['id'] for rule in rules}
    if not ids or len(ids) != len(rules):
        raise ValueError('Expected nonempty unique learned rules')
    if validation_manifest.get('rules_sha256') != digest or fuzz_manifest.get('rules_sha256') != digest:
        raise ValueError('Evaluation snapshots do not match exported rules')
    if validation_manifest.get('generation_profile') != 'expanded' or fuzz_manifest.get('generation_profile') != 'expanded':
        raise ValueError('Expanded generation evidence is required')
    results = validation.get('results', [])
    if (not validation.get('full_snapshot_verified') or validation.get('status') != 'completed'
            or len(results) != len(rules) or {item['rule_id'] for item in results} != ids
            or not all(item.get('passed') for item in results)):
        raise ValueError('Every exported rule needs successful expanded revalidation')
    if (fuzz.get('status') != 'completed' or fuzz.get('requested') != 10000
            or fuzz.get('executed') != 10000 or fuzz_manifest.get('count') != 10000):
        raise ValueError('A complete 10,000-query evaluation is required')
    if (validation_manifest.get('server_version') != fuzz_manifest.get('server_version')
            or validation_manifest.get('database') != fuzz_manifest.get('database')):
        raise ValueError('Evaluations used different database environments')
    return digest


def export_bundle(source: Path, validation: Path, fuzz: Path, output: Path):
    if output.exists():
        raise FileExistsError(output)
    rules_bytes = (source / 'trained_rules.json').read_bytes()
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    vm, vs = read(validation / 'manifest.json'), read(validation / 'summary.json')
    fm, fs = read(fuzz / 'manifest.json'), read(fuzz / 'summary.json')
    digest = check_evaluation(rules_bytes, vm, vs, fm, fs)
    if hashlib.sha256((fuzz / 'LearnedMySQL.g4').read_bytes()).hexdigest() != fm['grammar_sha256']:
        raise ValueError('Fuzz grammar differs from its manifest')
    # Recompute the fuzz denominator from retained executions, not summary alone.
    records = [json.loads(line) for line in (fuzz / 'sql_results.jsonl').read_text(encoding='utf-8').splitlines()]
    if (len(records) != 10000 or [row['index'] for row in records] != list(range(1, 10001))
            or sum(bool(row['ok']) for row in records) != fs['passed']
            or sum(row.get('antlr_error') is not None for row in records) != fs['antlr_errors']):
        raise ValueError('Fuzz summary disagrees with retained executions')
    output.mkdir(parents=True)
    # A failed gate leaves diagnostic evidence, never a delivery manifest.
    run_audit(source, output / 'training-audit')
    rules = [Rule(**item) for item in json.loads(rules_bytes)]
    for rule in rules:
        verdict = read(validation / 'trials' / rule.id / 'verdict.json')
        if verdict.get('generation_profile') != 'expanded':
            raise ValueError('Rule trial is missing expanded-profile evidence')
        verify_trial(validation / 'trials' / rule.id, rule, validation / 'parser_cache')
    if (source / 'trained_rules.json').read_bytes() != rules_bytes:
        raise ValueError('Source rules changed during export')
    (output / 'trained_rules.json').write_bytes(rules_bytes)
    mapping = compile_rules(ROOT / 'configs/mysql/MySQLBase.g4', rules, output / 'LearnedMySQL.g4')
    if hashlib.sha256((output / 'LearnedMySQL.g4').read_bytes()).hexdigest() != fm['grammar_sha256']:
        raise ValueError('Recompiled grammar differs from evaluated grammar')
    save(output / 'rule_map.json', mapping)
    for name in ('MySQLBase.g4', 'schema.json', 'schema.sql', 'semantics.json'):
        shutil.copy2(ROOT / 'configs/mysql' / name, output / name)
    copy_runtime_assets(output)
    save(output / 'evaluation.json', {'revalidation': vs, 'fuzz': fs, 'environment': fm})
    hashes = {str(path.relative_to(output)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in output.rglob('*') if path.is_file()}
    save(output / 'delivery_manifest.json', {'rules_sha256': digest, 'rules': len(rules),
         'server_version': fm['server_version'], 'generation_profile': 'expanded',
         'execution_accuracy': fs['passed'] / 10000, 'files': hashes})
    return output
