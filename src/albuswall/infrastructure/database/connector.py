#
"""
线程安全的 SQLite 数据库连接器，每个线程维护自己的连接。
"""

import sqlite3
import logging
import threading
from pathlib import Path
from importlib import resources
from typing import Optional

import albuswall
from albuswall.core.build_logger import TRACE

__all__ = [
    "DEFAULT_SCHEMA_FILE",
    "Connector"
]

# ============================================================================
# 可配置常量
# ============================================================================

DEFAULT_SCHEMA_FILE = (
    resources.files('albuswall.resources') /
    'sql' /
    'media_library_schema.sql'
)

MEMORY_DB_PATH = ":memory:"

PRAGMA_FOREIGN_KEYS_ON = "PRAGMA foreign_keys = ON"
PRAGMA_JOURNAL_WAL = "PRAGMA journal_mode=WAL"

CHECK_ASSETS_TABLE_SQL = (
    "SELECT name FROM sqlite_master "
    "WHERE type='table' AND name='assets'"
)

_package_name = __name__.split('.', 2)[-1] if '.' in __name__ else __name__


class Connector:
    """
    线程安全的 SQLite 数据库访问层，每个线程维护自己的连接。

    参数
    ----------
    db_path : str 或 None
        数据库文件路径。若为 None，连接时将自动使用内存数据库 (':memory:')。
    schema_file : Traversable, 可选
        建表 SQL 资源对象，默认使用内置资源。
    must_exist : bool, 可选
        若为 True，当 db_path 指定文件且不存在时，首次连接会抛出 FileNotFoundError。
        默认为 False（允许自动创建新文件）。

    使用方式：
        with db as conn:
            conn.execute("...")
    """
    logger = logging.getLogger(f"{albuswall.__name__}.{_package_name}")

    def __init__(self, db_path: Optional[str] = None,
                 schema_file=None,
                 must_exist: bool = False):
        # 仅保存原始参数，不做任何验证或转换
        self.db_path: Optional[str] = db_path
        self._must_exist = must_exist
        self._schema_file = schema_file or DEFAULT_SCHEMA_FILE
        self._schema_sql = self._load_schema(self._schema_file)

        # 线程安全与连接管理（__init__ 只声明变量）
        self._init_lock = threading.Lock()
        self._initialized = False
        self._local = threading.local()
        self._connections_lock = threading.Lock()
        self._connections: list[sqlite3.Connection] = []

        self.logger.debug("DB Connector init completed，db_path=%s, must_exist=%s",
                          self.db_path, self._must_exist)

    # ------------------------------------------------------------------
    # Schema 加载
    # ------------------------------------------------------------------
    @staticmethod
    def _load_schema(schema_resource):
        """从 importlib.resources 加载 SQL 文本"""
        try:
            return schema_resource.read_text(encoding='utf-8')
        except AttributeError:
            # 极旧版本回退
            with open(str(schema_resource), 'r', encoding='utf-8') as f:
                return f.read()

    # ------------------------------------------------------------------
    # 路径规范化（延迟到连接时执行）
    # ------------------------------------------------------------------
    def _resolve_db_path(self) -> str:
        """
        根据原始 db_path 返回实际连接使用的路径字符串。
        - None → ':memory:'
        - 非空字符串 → 解析为绝对路径
        """
        if self.db_path is None:
            self.logger.info("未指定数据库文件，使用内存数据库 '%s'", MEMORY_DB_PATH)
            return MEMORY_DB_PATH
        # 转为绝对路径，确保工作目录变化后仍指向同一文件
        absolute = Path(self.db_path).resolve()
        self.logger.info("数据库路径解析为: %s", absolute)
        return str(absolute)

    def _check_file_must_exist(self, resolved_path: str):
        """
        如果 must_exist=True 且不是内存数据库，检查文件是否存在。
        """
        if self._must_exist and resolved_path != MEMORY_DB_PATH:
            path = Path(resolved_path)
            if not path.exists():
                raise FileNotFoundError(f"数据库文件不存在且 must_exist=True: {resolved_path}")
            self.logger.debug("数据库文件存在检查通过: %s", resolved_path)

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
            self.logger.log(TRACE, "复用线程 %s 的现有连接", threading.current_thread().name)
        return self._local.connection

    def _create_connection(self) -> sqlite3.Connection:
        """
        为当前线程初始化一个新的连接，完成：
        - 路径解析与验证
        - 父目录创建（如需要）
        - 数据库连接与 pragma 设置
        - 首次 DDL 执行（全线程仅一次）
        """
        # 1. 解析最终数据库路径
        resolved = self._resolve_db_path()

        # 2. must_exist 检查（文件实际是否存在）
        self._check_file_must_exist(resolved)

        # 3. 非内存库则确保父目录存在
        if resolved != MEMORY_DB_PATH:
            Path(resolved).parent.mkdir(parents=True, exist_ok=True)
            self.logger.debug("数据库父目录已确保存在: %s", Path(resolved).parent)

        # 4. 建立连接，配置参数
        conn = sqlite3.connect(resolved)
        conn.row_factory = sqlite3.Row
        conn.execute(PRAGMA_FOREIGN_KEYS_ON)
        conn.execute(PRAGMA_JOURNAL_WAL)
        self.logger.debug("新连接已创建，路径: %s，外键约束已启用，日志模式: WAL", resolved)

        # 5. 全线程仅一次 DDL 初始化
        if not self._initialized:
            with self._init_lock:
                if not self._initialized:  # 双重检查
                    table_exists = conn.execute(CHECK_ASSETS_TABLE_SQL).fetchone()
                    if not table_exists:
                        self.logger.info("首次创建数据库，开始执行 Schema ...")
                        conn.executescript(self._schema_sql)
                        self.logger.info("Schema 创建完成")
                    else:
                        self.logger.debug("数据库已存在，跳过建表，执行幂等索引补全")
                        conn.executescript(self._schema_sql)  # 语句均含 IF NOT EXISTS
                    self._initialized = True

        return conn

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
    # 上下文管理器
    # ------------------------------------------------------------------
    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 退出不关闭连接，保持线程复用
        return False
