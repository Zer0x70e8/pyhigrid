#
""""""

import os
import sqlite3
from typing import cast
from pathlib import Path

import pyhigrid

__all__ = [
    "DEFAULT_SCHEMA_FILE",
    "Database"
]

DEFAULT_SCHEMA_FILE = (Path(pyhigrid.__file__).parent /
                       "resources" / "sql" / "media_library_schema.sql"
                       )

class Database:
    def __init__(self, db_path=None, schema_file=None):
        self.db_path: Path = db_path
        self._connection: None = None
        self.__schema_sql = self._load_schema(schema_file or DEFAULT_SCHEMA_FILE)

    @property
    def connection(self):
        return self._connection

    @property
    def schema_sql(self):
        return self.__schema_sql
    @schema_sql.setter
    def schema_sql(self, value):
        """这里添加安全验证逻辑，目前仅预留"""
        self.__schema_sql = cast(str, value)

    @staticmethod
    def _load_schema(path):
        """从 .sql 文件读取建表语句"""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def init_db(self):
        # 只对真实文件路径创建目录，跳过 :memory: 或空路径
        if self.db_path not in (":memory:", "", None):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._connection = sqlite3.connect(str(self.db_path))
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")

        table_exists = self._connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='assets'"
        ).fetchone()

        if not table_exists:
            self._connection.executescript(self.__schema_sql)

    def connect(self):
        """获取或创建连接（懒加载）"""
        if self._connection is None:
            self.init_db()

        return self._connection

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
