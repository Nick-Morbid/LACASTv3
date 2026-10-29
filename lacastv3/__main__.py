import argparse
from pathlib import Path

from dotenv import load_dotenv

from .database import MySQLDatabase
from .training import Trainer, exclusive_run
from .fuzz import run_fuzz
from .audit import run_audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['train', 'fuzz', 'audit'])
    parser.add_argument('--dbms', choices=['mysql'], default='mysql')
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--db-config', type=Path)
    parser.add_argument('--feature-limit', type=int, default=0,
                        help='Diagnostic only; zero processes the full corpus')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--count', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--allow-partial', action='store_true', help='Audit retained rules during an incomplete run')
    args = parser.parse_args()
    load_dotenv()
    db = MySQLDatabase(config_file=args.db_config)
    if args.command == 'train':
        with exclusive_run(args.work_dir):
            Trainer(args.work_dir, db, args.feature_limit).run()
    elif args.command == 'fuzz':
        if args.output is None:
            parser.error('fuzz requires --output (a new result directory)')
        run_fuzz(args.work_dir, args.output, db, args.count, args.seed)
    else:
        if args.output is None:
            parser.error('audit requires --output (a new result directory)')
        run_audit(args.work_dir, args.output, args.allow_partial)


if __name__ == '__main__':
    main()
