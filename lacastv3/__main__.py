import argparse
from pathlib import Path

from dotenv import load_dotenv

from .database import MySQLDatabase
from .training import Trainer, exclusive_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['train'])
    parser.add_argument('--dbms', choices=['mysql'], default='mysql')
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--db-config', type=Path)
    parser.add_argument('--feature-limit', type=int, default=0,
                        help='Diagnostic only; zero processes the full corpus')
    args = parser.parse_args()
    load_dotenv()
    db = MySQLDatabase(config_file=args.db_config)
    with exclusive_run(args.work_dir):
        Trainer(args.work_dir, db, args.feature_limit).run()


if __name__ == '__main__':
    main()
