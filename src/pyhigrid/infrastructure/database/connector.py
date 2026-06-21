#
"""
线程安全的 SQLite 数据库连接器，每个线程维护自己的连接。
"""

import sqlite3
import threading
from pathlib import Path
from importlib import resources

from pyhigrid import __name__ as __main_package_name__
from pyhigrid.configue.utils.logger_descriptor import LazyLogger

__all__ = [
    "DEFAULT_SCHEMA_FILE",
    "Connector"
]

# ============================================================================
# 可配置常量
# ============================================================================

# 使用 importlib.resources 加载资源（仅保存 Traversable 对象）
DEFAULT_SCHEMA_FILE = (
    resources.files('pyhigrid.resources') /
    'sql' /
    'media_library_schema.sql'
)

# 连接时无需创建父目录的特殊路径（转为字符串后再比较）
SKIP_DIR_CREATION_DB_PATHS = {":memory:", "", None}

# 数据库连接初始化设置
PRAGMA_FOREIGN_KEYS_ON = "PRAGMA foreign_keys = ON"
PRAGMA_JOURNAL_WAL = "PRAGMA journal_mode=WAL"

# 用于首次建库检测
CHECK_ASSETS_TABLE_SQL = (
    "SELECT name FROM sqlite_master "
    "WHERE type='table' AND name='assets'"
)

_package_name = __name__.split('.')[-1] if '.' in __name__ else __name__


class Connector:
    """
    线程安全的 SQLite 数据库访问层，每个线程维护自己的连接。

    使用方式：
        with db as conn:
            conn.execute("...")
    """
    logger = LazyLogger(f"{__main_package_name__}.{_package_name}")

    def __init__(self, db_path=None, schema_file=None):
        # 🔧 统一将路径转为字符串，方便后续判断
        self.db_path: str = str(db_path) if db_path else None
        self._schema_file = schema_file or DEFAULT_SCHEMA_FILE

        # 🔧 使用资源对象的 read_text() 方法加载 SQL（兼容 Python 3.9+）
        self._schema_sql = self._load_schema(self._schema_file)

        # 🔧 线程安全标志：确保 DDL 只执行一次
        self._init_lock = threading.Lock()
        self._initialized = False

        # 每个线程独立的连接，惰性创建
        self._local = threading.local()
        self._connections_lock = threading.Lock()
        self._connections: list[sqlite3.Connection] = []

        self.logger.info("DB Connector init completed, DB path: %s", self.db_path)

    # ------------------------------------------------------------------
    # Schema 管理
    # ------------------------------------------------------------------
    @staticmethod
    def _load_schema(schema_resource):
        """🔧 从 importlib.resources 的 Traversable 对象加载 SQL"""
        try:
            # Python ≥3.11 可直接 .read_text()，3.9+ 也可用 contextlib 兼容
            return schema_resource.read_text(encoding='utf-8')
        except AttributeError:
            # 极旧版本回退（理论上不会发生）
            with open(str(schema_resource), 'r', encoding='utf-8') as f:
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
        """为当前线程初始化一个新的连接，完成建表（仅首次）和连接级设置"""
        # 🔧 创建目录前，精准判断是否需要创建
        need_mkdir = self.db_path and str(self.db_path) not in SKIP_DIR_CREATION_DB_PATHS
        if need_mkdir:
            # 安全地创建父目录
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self.logger.debug("已确保数据库目录存在: %s", Path(self.db_path).parent)

        # 连接数据库
        conn = sqlite3.connect(self.db_path if self.db_path else ":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(PRAGMA_FOREIGN_KEYS_ON)
        # 🔧 WAL 模式在每个连接都设置一次（持久化后无害）
        conn.execute(PRAGMA_JOURNAL_WAL)

        # 🔧 首次初始化 DDL，加锁保证多线程只执行一次
        if not self._initialized:
            with self._init_lock:
                if not self._initialized:  # 双重检查
                    table_exists = conn.execute(CHECK_ASSETS_TABLE_SQL).fetchone()
                    if not table_exists:
                        self.logger.info("首次创建数据库，开始执行 Schema ...")
                        conn.executescript(self._schema_sql)
                        self.logger.info("Schema 创建完成")
                    else:
                        self.logger.debug("数据库已存在，跳过建表，但仍确保索引存在")
                        # 对已存在的库，用幂等方式补全索引（无副作用）
                        conn.executescript(self._schema_sql)  # 所有语句都 IF NOT EXISTS
                    self._initialized = True

        self.logger.debug("新连接已建立并启用外键约束")
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
