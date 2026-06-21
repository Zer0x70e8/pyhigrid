#
"""基础仓库类，提供通用数据库访问能力及事务上下文。"""

from contextlib import contextmanager
from sqlite3 import Cursor, Row, Connection
from typing import Optional, List, Generator

from pyhigrid.infrastructure.database import Connector
from pyhigrid.configue.utils.logger_descriptor import LazyLogger


class BaseRepository:
    """仓库基类，封装线程安全的读写与事务。"""

    logger = LazyLogger("__main__.database")

    def __init__(self, db: Connector):
        self._db: Connector = db

    # ---------- 原有便捷方法 ----------
    def _execute(self,
                 query: str,
                 params=None
                 ) -> Cursor:
        with self._db.connect() as conn:
            cursor = conn.execute(query, params or ())
            conn.commit()
            return cursor

    def _fetchone(self,
                  query: str,
                  params=None
                  ) -> Optional[Row]:
        with self._db.connect() as conn:
            cursor = conn.execute(query, params or ())
            return cursor.fetchone()

    def _fetchall(self,
                  query: str,
                  params=None
                  ) -> Optional[List[Row]]:
        with self._db.connect() as conn:
            cursor = conn.execute(query, params or ())
            return cursor.fetchall()

    @contextmanager
    def _transaction(self) -> Generator[Connection, None, None]:
        conn: Connection = self._db.connect()
        if conn is None:
            raise RuntimeError("数据库连接获取失败")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            self.logger.exception("事务回滚，已发生异常")
            raise
