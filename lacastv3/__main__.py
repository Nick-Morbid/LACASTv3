import argparse
from pathlib import Path

from dotenv import load_dotenv

from .database import MySQLDatabase
from .training import Trainer, exclusive_run
from .fuzz import run_fuzz
from .audit import run_audit
from .revalidate import run_revalidation
from .delivery import export_bundle
from .reconcile import import_evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['train', 'fuzz', 'audit', 'revalidate', 'export', 'import-evidence'])
    parser.add_argument('--dbms', choices=['mysql'], default='mysql')
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--db-config', type=Path)
    parser.add_argument('--feature-limit', type=int, default=0,
                        help='Diagnostic only; zero processes the full corpus')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--validation-dir', type=Path)
    parser.add_argument('--fuzz-dir', type=Path)
    parser.add_argument('--trial', type=Path)
    parser.add_argument('--feature-key')
    parser.add_argument('--replace-rule')
    parser.add_argument('--count', type=int, default=10000)
    parser.add_argument('--rule-limit', type=int, default=0, help='Diagnostic revalidation limit; zero checks all rules')
    parser.add_argument('--resume', action='store_true', help='Resume an interrupted revalidation snapshot')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--generation-profile', choices=['baseline', 'expanded'], default='expanded')
    parser.add_argument('--allow-partial', action='store_true', help='Audit retained rules during an incomplete run')
    args = parser.parse_args()
    load_dotenv()
    db = MySQLDatabase(config_file=args.db_config)
    if args.command == 'train':
        with exclusive_run(args.work_dir):
            Trainer(args.work_dir, db, args.feature_limit, args.generation_profile).run()
    elif args.command == 'fuzz':
        if args.output is None:
            parser.error('fuzz requires --output (a new result directory)')
        run_fuzz(args.work_dir, args.output, db, args.count, args.seed, args.generation_profile)
    elif args.command == 'import-evidence':
        if args.trial is None or args.feature_key is None:
            parser.error('import-evidence requires --trial and --feature-key')
        import_evidence(args.work_dir, args.trial, args.feature_key, args.replace_rule)
    elif args.command == 'export':
        if args.output is None or args.validation_dir is None or args.fuzz_dir is None:
            parser.error('export requires --output, --validation-dir and --fuzz-dir')
        export_bundle(args.work_dir, args.validation_dir, args.fuzz_dir, args.output)
    elif args.command == 'revalidate':
        if args.output is None:
            parser.error('revalidate requires --output (a new result directory)')
        run_revalidation(args.work_dir, args.output, db, args.seed, args.rule_limit, args.resume)
    else:
        if args.output is None:
            parser.error('audit requires --output (a new result directory)')
        run_audit(args.work_dir, args.output, args.allow_partial)


if __name__ == '__main__':
    main()
