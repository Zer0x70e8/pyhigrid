#
""""""

import os
import sqlite3
import threading
from pathlib import Path
from typing import cast

import pyhigrid

__all__ = [
    "DEFAULT_SCHEMA_FILE",
    "Database"
]

DEFAULT_SCHEMA_FILE = (
    Path(pyhigrid.__file__).parent / "resources" / "sql" / "media_library_schema.sql"
)


class Database:
    """
    线程安全的 SQLite 数据库访问层，每个线程维护自己的连接。

    使用方式：
        with db as conn:
            conn.execute("...")
    """

    def __init__(self, db_path=None, schema_file=None):
        self.db_path: Path = db_path
        self._schema_file = schema_file or DEFAULT_SCHEMA_FILE
        self.__schema_sql = self._load_schema(self._schema_file)

        # 每个线程独立的连接，惰性创建
        self._local = threading.local()
        # 可选：记录所有打开的连接，方便全局关闭
        self._connections_lock = threading.Lock()
        self._connections: list[sqlite3.Connection] = []

    # ------------------------------------------------------------------
    # Schema 管理（不变）
    # ------------------------------------------------------------------
    @property
    def schema_sql(self):
        return self.__schema_sql

    @schema_sql.setter
    def schema_sql(self, value):
        """预留安全验证逻辑"""
        self.__schema_sql = cast(str, value)

    @staticmethod
    def _load_schema(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    # ------------------------------------------------------------------
    # 连接获取（改造为线程本地）
    # ------------------------------------------------------------------
    def connect(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接（惰性创建）"""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            conn = self._create_connection()
            self._local.connection = conn
            with self._connections_lock:
                self._connections.append(conn)
        return self._local.connection

    def _create_connection(self) -> sqlite3.Connection:
        """为当前线程初始化一个新的连接，同时完成建表和索引"""
        # 创建目录（仅真实文件路径）
        if self.db_path not in (":memory:", "", None):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        # 解决多线程共享连接的问题 —— 每个线程独自使用自己的连接，
        # 所以不需要 check_same_thread=False，这反而更安全。
        # 注意：因为每个线程独立 connect，所以不需要这个参数。

        # 建表（仅当 assets 表不存在时）
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='assets'"
        ).fetchone()

        if not table_exists:
            conn.executescript(self.__schema_sql)
            # 表创建后再补充索引和约束，这部分永远跟随新建库执行
            self._apply_indexes(conn)

        # 对已存在的库，也用 IF NOT EXISTS 保证索引存在（幂等）
        self._apply_indexes(conn)

        return conn

    def _apply_indexes(self, conn: sqlite3.Connection):
        """创建性能和数据完整性所必需的索引与约束"""
        # 注意：SQLite 不支持 CREATE UNIQUE INDEX ... WHERE（部分唯一索引）
        # 但可以用一个无法插入重复的触发器，或使用带 NULL 的替换方法。
        # 这里改为在 assets 表上创建唯一索引用于去重，
        # 同时依赖应用程序逻辑保证同一哈希只有一条 is_deleted=0 的记录。
        # 更安全的做法：创建一个唯一索引作用于 (file_hash, is_deleted) 上
        # 但 NULL 不被视为相等，所以可以用 COALESCE 或改用：
        # 但 SQLite 3.8.0+ 支持 WHERE 子句的唯一索引，可以写：
        # CREATE UNIQUE INDEX idx_active_assets ON assets(file_hash) WHERE is_deleted = 0;
        # 这里假设使用较新版本 SQLite。
        indexes = [
            # 活跃资产哈希唯一，防止重复导入
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_assets_active_hash "
            "ON assets(file_hash) WHERE is_deleted = 0;",

            # 快速过滤常用状态
            "CREATE INDEX IF NOT EXISTS idx_assets_deleted ON assets(is_deleted);",
            "CREATE INDEX IF NOT EXISTS idx_assets_favorite ON assets(is_favorite);",

            # 导入时查找内置相簿
            "CREATE INDEX IF NOT EXISTS idx_albums_uuid ON albums(uuid);",

            # album_assets 关联查询及排序
            "CREATE INDEX IF NOT EXISTS idx_album_assets_album ON album_assets(album_id, asset_id);",
            "CREATE INDEX IF NOT EXISTS idx_album_assets_added ON album_assets(album_id, added_at);",
            "CREATE INDEX IF NOT EXISTS idx_album_assets_sort ON album_assets(album_id, sort_order, asset_id);",
            "CREATE INDEX IF NOT EXISTS idx_album_assets_taken ON album_assets(album_id, asset_taken_at);",
        ]

        # 为 album_assets 添加复合主键（防止重复映射）
        # 先检查表结构，如果不存在主键则添加（仅在全新创建时有效）
        # 稳妥做法：在 schema.sql 中直接定义 PRIMARY KEY (album_id, asset_id)
        # 这里用额外语句尝试创建唯一索引：
        indexes.append(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_album_assets_unique "
            "ON album_assets(album_id, asset_id);"
        )

        for sql in indexes:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError as e:
                # 如果 SQLite 版本不支持部分唯一索引，回退到普通索引
                if "WHERE" in sql and "UNIQUE" in sql:
                    fallback = sql.replace(" WHERE is_deleted = 0", "")
                    fallback = fallback.replace("CREATE UNIQUE INDEX IF NOT EXISTS",
                                                "CREATE INDEX IF NOT EXISTS")
                    try:
                        conn.execute(fallback)
                    except Exception:
                        pass
                # 否则忽略（例如重复创建等非致命错误）
                else:
                    pass

    # ------------------------------------------------------------------
    # 关闭连接（支持线程级别和全局）
    # ------------------------------------------------------------------
    def close(self):
        """关闭当前线程的连接"""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            conn = self._local.connection
            conn.close()
            self._local.connection = None
            with self._connections_lock:
                if conn in self._connections:
                    self._connections.remove(conn)

    def close_all(self):
        """关闭所有线程的数据库连接（通常在程序退出时调用）"""
        with self._connections_lock:
            for conn in list(self._connections):
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()

    # ------------------------------------------------------------------
    # 上下文管理器（线程安全，返回当前线程连接）
    # ------------------------------------------------------------------
    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 上下文退出不关闭连接，保持线程复用
        return False