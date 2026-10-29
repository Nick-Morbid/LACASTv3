"""Revalidate a fixed learned-rule snapshot without touching the live trainer."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .audit import verify_trial
from .training import Trainer, save


def run_revalidation(source: Path, output: Path, db, seed=0, rule_limit=0):
    if rule_limit < 0:
        raise ValueError('Rule limit must be nonnegative')
    if output.exists():
        raise FileExistsError(output)
    # Atomic trainer writes make a single read a coherent immutable snapshot.
    snapshot = (source / 'trained_rules.json').read_bytes()
    output.mkdir(parents=True)
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
    save(output / 'manifest.json', manifest)
    rules = trainer.accepted[:rule_limit] if rule_limit else trainer.accepted
    results = []
    status = 'running'
    try:
        for index, rule in enumerate(rules):
            trial = output / 'trials' / rule.id
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
