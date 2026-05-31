#
""""""

import os
from sqlite3 import Cursor, Row
from typing import Optional, List

from pyhigrid.configue.utils.logger_descriptor import LazyLogger
from pyhigrid.infrastructure.database import Connector

_package_name = os.path.basename(os.path.dirname(__file__))

class BaseRepository:
    logger = LazyLogger(f"__main__.{_package_name}")

    def __init__(self, db: Connector):
        self._db = db
        self.logger.info(f"Initializing repository: {type(self).__name__}")

    # write
    def _execute(self,
                 query: str,
                 params=None
                 ) -> Cursor:
        """执行 INSERT/UPDATE/DELETE, auto commit."""
        with self._db.connect() as conn:
            cursor = conn.execute(query, params or ())
            conn.commit()
            return cursor

    # read
    def _fetchone(self,
                  query: str,
                  params=None
                  ) -> Optional[Row]:
        """查询单行，:return: sqlite3.Row or None."""
        with self._db.connect() as conn:
            cursor = conn.execute(query, params or ())
            return cursor.fetchone()

    def _fetchall(self,
                  query: str,
                  params=None
                  ) -> Optional[List[Row]]:
        """查询多行，:return: list of sqlite3.Row."""
        with self._db.connect() as conn:
            cursor = conn.execute(query, params or ())
            return cursor.fetchall()
