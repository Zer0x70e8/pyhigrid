#
"""
线程安全的 SQLite 数据库连接器，每个线程维护自己的连接。
"""

import os
import sqlite3
import threading
from pathlib import Path
from typing import cast
from importlib import resources

from pyhigrid.configue.utils.logger_descriptor import LazyLogger

__all__ = [
    "DEFAULT_SCHEMA_FILE",
    "Connector"
]

# ============================================================================
# 可配置常量
# ============================================================================

# 默认的数据库 Schema 文件路径（相对于当前文件位置的 resources 目录）
DEFAULT_SCHEMA_FILE = (
        resources.files('pyhigrid.resources') /
        'sql' /
        'media_library_schema.sql'
)

# 特殊数据库路径：连接时无需创建父目录
SKIP_DIR_CREATION_DB_PATHS = (":memory:", "", None)

# 数据库连接初始化设置
PRAGMA_FOREIGN_KEYS_ON = "PRAGMA foreign_keys = ON"

# 用于检查 assets 表是否已存在的 SQL
CHECK_ASSETS_TABLE_SQL = (
    "SELECT name FROM sqlite_master "
    "WHERE type='table' AND name='assets'"
)

# 主要表名（用于索引创建等）
ASSETS_TABLE = "assets"
ALBUMS_TABLE = "albums"
ALBUM_ASSETS_TABLE = "album_assets"

_package_name = os.path.basename(os.path.dirname(__file__))

class Connector:
    """
    线程安全的 SQLite 数据库访问层，每个线程维护自己的连接。

    使用方式：
        with db as conn:
            conn.execute("...")
    """
    logger = LazyLogger(f"__main__.{_package_name}")

    def __init__(self, db_path=None, schema_file=None):
        self.db_path: Path = db_path
        self._schema_file = schema_file or DEFAULT_SCHEMA_FILE
        self.__schema_sql = self._load_schema(self._schema_file)

        # 每个线程独立的连接，惰性创建
        self._local = threading.local()
        # 可选：记录所有打开的连接，方便全局关闭
        self._connections_lock = threading.Lock()
        self._connections: list[sqlite3.Connection] = []

        self.logger.info("DB Connector init completed，DB path: %s", self.db_path)

    # ------------------------------------------------------------------
    # Schema 管理
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
    # 连接获取（线程本地）
    # ------------------------------------------------------------------
    def connect(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接（惰性创建）"""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self.logger.debug("为线程 %s 创建新连接", threading.current_thread().name)
            conn = self._create_connection()
            self._local.connection = conn
            with self._connections_lock:
                self._connections.append(conn)
        else:
            self.logger.debug("复用线程 %s 的现有连接", threading.current_thread().name)
        return self._local.connection

    def _create_connection(self) -> sqlite3.Connection:
        """为当前线程初始化一个新的连接，同时完成建表和索引"""
        # 创建目录（仅真实文件路径）
        if self.db_path not in SKIP_DIR_CREATION_DB_PATHS:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.logger.debug("已确保数据库目录存在: %s", self.db_path.parent)

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute(PRAGMA_FOREIGN_KEYS_ON)
        self.logger.debug("新连接已建立并启用外键约束")

        # 建表（仅当 assets 表不存在时）
        table_exists = conn.execute(CHECK_ASSETS_TABLE_SQL).fetchone()

        if not table_exists:
            self.logger.info("assets 表不存在，开始初始化数据库 Schema")
            conn.executescript(self.__schema_sql)
            self.logger.info("Schema 创建完成，开始应用索引与约束")
            self._apply_indexes(conn)
        else:
            self.logger.debug("数据库已包含 assets 表，跳过 Schema 创建，直接确保索引存在")
            # 对已存在的库，也用 IF NOT EXISTS 保证索引存在（幂等）
            self._apply_indexes(conn)

        return conn

    @staticmethod
    def _apply_indexes(conn: sqlite3.Connection):
        """创建性能和数据完整性所必需的索引与约束"""
        logger = Connector.logger  # 静态方法中引用类级日志器

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
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_album_assets_unique "
            "ON album_assets(album_id, asset_id);"
        ]

        for sql in indexes:
            try:
                conn.execute(sql)
                logger.debug("索引/约束应用成功: %s", sql[:60])
            except sqlite3.OperationalError as oe:
                # 如果 SQLite 版本不支持部分唯一索引，回退到普通索引
                if "WHERE" in sql and "UNIQUE" in sql:
                    fallback = sql.replace(" WHERE is_deleted = 0", "")
                    fallback = fallback.replace("CREATE UNIQUE INDEX IF NOT EXISTS",
                                                "CREATE INDEX IF NOT EXISTS")
                    try:
                        conn.execute(fallback)
                        logger.info("因版本限制，已使用回退索引: %s", fallback[:60])
                    except Exception as e:
                        logger.warning("回退索引创建失败: %s，错误: %s", fallback[:60], e)
                else:
                    logger.warning("索引创建出现非致命错误: %s，SQL: %s", oe, sql[:60])
        conn.commit()  # 确保索引创建持久化

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
            self.logger.debug("线程 %s 的连接已关闭", threading.current_thread().name)
        else:
            self.logger.debug("线程 %s 无活动连接，忽略关闭", threading.current_thread().name)

    def close_all(self):
        """关闭所有线程的数据库连接（通常在程序退出时调用）"""
        with self._connections_lock:
            count = len(self._connections)
            for conn in list(self._connections):
                try:
                    conn.close()
                except Exception as e:
                    self.logger.warning("关闭连接时出现异常: %s", e)
            self._connections.clear()
        self.logger.info("已关闭所有线程的数据库连接，共 %d 个", count)

    # ------------------------------------------------------------------
    # 上下文管理器（线程安全，返回当前线程连接）
    # ------------------------------------------------------------------
    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 上下文退出不关闭连接，保持线程复用
        return False
