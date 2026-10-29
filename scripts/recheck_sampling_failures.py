"""Recheck previously inconclusive candidates without mutating active training."""
import argparse
import json
from pathlib import Path

from lacastv3.database import MySQLDatabase
from lacastv3.productions import Rule
from lacastv3.training import Trainer, save

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--db-config', type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
events = [json.loads(line) for line in (args.source / 'events.jsonl').read_text(encoding='utf-8').splitlines()]
passed = {event['rule_id'] for event in events if event['event'] == 'rule_verdict' and event.get('passed')}
pending = {event['rule_id']: event['feature'] for event in events
           if event['event'] == 'rule_verdict' and event.get('error', '').startswith('Incomplete target sample')
           and event['rule_id'] not in passed}
definitions = {item['id']: item for path in (args.source / 'features').glob('*/candidates-*.json')
               for item in json.loads(path.read_text())}
trainer = Trainer(args.output, MySQLDatabase(config_file=args.db_config))
trainer.accepted = [Rule(**item) for item in json.loads((args.source / 'trained_rules.json').read_text())]
results = []
for rule_id, feature in pending.items():
    rule = Rule(**definitions[rule_id])
    try:
        verdict = trainer.evaluate(rule, args.output / f'trial-{rule_id}', seed=0)
    except Exception as error:
        verdict = {'passed': False, 'error': str(error)}
    results.append({'feature': feature, 'rule': definitions[rule_id], 'verdict': verdict})
save(args.output / 'recheck.json', results)
print(json.dumps({'checked': len(results), 'passed': sum(item['verdict']['passed'] for item in results),
                  'output': str(args.output.resolve())}, indent=2))
