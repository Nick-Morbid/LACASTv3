"""Revalidate a fixed learned-rule snapshot without touching the live trainer."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .audit import verify_trial
from .training import ROOT, Trainer, save, exclusive_run
from .provenance import capture_runtime


def run_revalidation(source: Path, output: Path, db, seed=0, rule_limit=0, resume=False):
    if rule_limit < 0:
        raise ValueError('Rule limit must be nonnegative')
    if resume:
        if not output.is_dir():
            raise FileNotFoundError(output)
    else:
        output.mkdir(parents=True, exist_ok=False)
    with exclusive_run(output):
        return _run_revalidation(source, output, db, seed, rule_limit, resume)


def _run_revalidation(source, output, db, seed, rule_limit, resume):
    # Atomic trainer writes make a single read a coherent immutable snapshot.
    snapshot = ((output if resume else source) / 'trained_rules.json').read_bytes()
    if not resume:
        (output / 'trained_rules.json').write_bytes(snapshot)
    trainer = Trainer(output, db, generation_profile='expanded')
    with db.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT VERSION(), DATABASE(), @@sql_mode')
            version, database, sql_mode = cursor.fetchone()
    manifest = {'source': str(source.resolve()), 'started_at': datetime.now(timezone.utc).isoformat(),
                'rules_sha256': hashlib.sha256(snapshot).hexdigest(),
                'generation_profile': 'expanded', 'server_version': version,
                'database': database, 'sql_mode': sql_mode, 'seed': seed,
                'snapshot_rules': len(trainer.accepted), 'rule_limit': rule_limit}
    results = []
    if resume:
        original = json.loads((output / 'manifest.json').read_text())
        for key in ('source', 'rules_sha256', 'generation_profile', 'server_version', 'database', 'sql_mode', 'seed', 'rule_limit'):
            if original.get(key) != manifest[key]:
                raise ValueError(f'Revalidation resume changed {key}')
        manifest = original
        progress = output / 'progress.json'
        results = json.loads(progress.read_text())['results'] if progress.exists() else []
    attempt = output / 'runtime-attempts' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    attempt.mkdir(parents=True)
    runtime = capture_runtime(ROOT, attempt)
    manifest.setdefault('runtime_history', []).append({'first_rule_index': len(results),
        'directory': str(attempt.relative_to(output)), 'runtime': runtime})
    save(output / 'manifest.json', manifest)
    rules = trainer.accepted[:rule_limit] if rule_limit else trainer.accepted
    if [item['rule_id'] for item in results] != [rule.id for rule in rules[:len(results)]]:
        raise ValueError('Saved progress is not a prefix of the immutable rule snapshot')
    status = 'running'
    try:
        for index, rule in enumerate(rules):
            if index < len(results):
                continue
            trial = output / 'trials' / rule.id
            if trial.exists():
                archive = output / 'interrupted-trials' / (rule.id + '-' + attempt.name)
                if not trial.resolve().is_relative_to(output.resolve()) or not archive.resolve().is_relative_to(output.resolve()):
                    raise ValueError('Interrupted trial archive escaped output directory')
                archive.parent.mkdir(parents=True, exist_ok=True)
                trial.rename(archive)
            try:
                verdict = trainer.evaluate(rule, trial, seed + index * 10000)
                result = {'rule_id': rule.id, 'passed': verdict['passed']}
                if verdict['passed']:
                    result['audit'] = verify_trial(trial, rule, output / 'parser_cache')
            except Exception as error:
                result = {'rule_id': rule.id, 'passed': False, 'error': str(error)}
            results.append(result)
            save(output / 'progress.json', {'checked': len(results), 'requested': len(rules),
                 'passed': sum(item['passed'] for item in results), 'results': results})
            print(f"{index+1}/{len(rules)} {rule.id} passed={result['passed']}", flush=True)
        status = 'completed'
    finally:
        save(output / 'summary.json', {'status': status if status == 'completed' else 'interrupted',
             'checked': len(results), 'requested': len(rules), 'snapshot_rules': len(trainer.accepted),
             'passed': sum(item['passed'] for item in results),
             'full_snapshot_verified': status == 'completed' and len(results) == len(trainer.accepted)
                 and bool(results) and all(item['passed'] for item in results),
             'generation_profile': 'expanded', 'results': results})
    return results
