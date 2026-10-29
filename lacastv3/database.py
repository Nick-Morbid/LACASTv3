"""MySQL execution with dedicated initialization and complete result fetching."""
import os
from pathlib import Path

import mysql.connector
import yaml


class MySQLDatabase:
    def __init__(self, database=None, config_file: Path | None = None):
        config = {}
        if config_file:
            config = yaml.safe_load(config_file.read_text(encoding='utf-8'))['db_config']
        self.settings = {
            'host': os.getenv('MYSQL_HOST', config.get('host', '127.0.0.1')),
            'port': int(os.getenv('MYSQL_PORT', config.get('port', 3306))),
            'user': os.getenv('MYSQL_USER', config.get('username', 'root')),
            'password': os.getenv('MYSQL_PASSWORD', config.get('password', '')),
            'connection_timeout': 10,
        }
        self.database = database or os.getenv('MYSQL_DATABASE', 'lacastv3_mysql')

    def connect(self):
        conn = mysql.connector.connect(**self.settings, database=self.database)
        with conn.cursor() as cursor:
            cursor.execute('SET SESSION max_execution_time = 30000')
            cursor.execute("SET SESSION sql_mode = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'")
        return conn

    def initialize(self, schema: Path):
        if not self.database.startswith('lacastv3_') or not self.database.replace('_', '').isalnum():
            raise ValueError('Initialization requires a dedicated lacastv3_ database')
        conn = mysql.connector.connect(**self.settings)
        try:
            with conn.cursor() as cursor:
                cursor.execute(f'CREATE DATABASE IF NOT EXISTS `{self.database}` CHARACTER SET utf8mb4')
        finally:
            conn.close()
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(schema.read_text(encoding='utf-8'), map_results=True)
                while True:
                    if cursor.with_rows:
                        cursor.fetchall()
                    if not cursor.nextset():
                        break
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def execute(conn, sql):
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall() if cursor.with_rows else []
                description = cursor.description
            conn.rollback()
            return {'ok': True, 'rows': len(rows), 'columns': [item[0] for item in description or []]}
        except mysql.connector.Error as error:
            conn.rollback()
            return {'ok': False, 'errno': error.errno, 'sqlstate': error.sqlstate, 'error': str(error)}
