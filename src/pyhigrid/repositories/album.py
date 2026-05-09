#
""""""

import sqlite3
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from pyhigrid.schemas.entities import Album, Asset
from pyhigrid.schemas.enums import AlbumAssetSortOption

if TYPE_CHECKING:
    from pyhigrid.db import Database  # noqa


class AlbumRepository:
    """相簿与相簿资产只读仓库"""

    def __init__(self, database: "Database"):
        self._db_ref = database
        # 通过 property 惰性获取连接，保证线程安全的时间由调用方控制
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = self._db_ref.connect()
        return self._conn

    # ------------------------------------------------------------------
    # 相簿本身
    # ------------------------------------------------------------------
    def get_all_albums(self) -> List[Album]:
        rows = self.conn.execute(
            "SELECT id, uuid, title, album_type, cover_asset_id, sort_order, is_deleted "
            "FROM albums WHERE is_deleted = 0 ORDER BY sort_order"
        ).fetchall()
        return [Album(**dict(r)) for r in rows]

    def get_album(self, album_id: int) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT id, uuid, title, album_type, cover_asset_id, sort_order, is_deleted "
            "FROM albums WHERE id = ? AND is_deleted = 0", (album_id,)
        ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # 相簿内的资产
    # ------------------------------------------------------------------
    def get_album_assets(
            self,
            album_id: int,
            sort_by: AlbumAssetSortOption = AlbumAssetSortOption.TAKEN_AT,
            limit: int = 50,
            offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        获取指定相簿中的资产列表，内置相簿自动使用正确过滤条件。

        支持的 sort_by:
            - "taken_at"   (默认，拍摄时间降序)
            - "added_at"   (添加时间降序，仅对手动相簿有效，其它退回 taken_at)
            - "sort_order" (手动排序，仅对手动相簿有效)
        """
        album = self.get_album(album_id)
        if not album:
            return []

        query, params = self._build_asset_query(album, sort_by, limit, offset)
        return [dict(r) for r in self.conn.execute(query, params).fetchall()]

    def _build_asset_query(self, album: Dict[str, Any], sort_by: str,
                           limit: int, offset: int):
        """根据相簿类型返回 (SQL, 参数)"""
        album_type = album["album_type"]
        # 手动相簿 / 智能相簿 (0,1)
        if album_type in (0, 1):
            # ---------- 手动相簿直接查 album_assets ----------
            order_clause = self._order_clause_for_manual(sort_by)
            sql = f"""
                SELECT a.*
                FROM assets a
                JOIN album_assets aa ON a.id = aa.asset_id
                WHERE aa.album_id = ?
                ORDER BY {order_clause}
                LIMIT ? OFFSET ?
            """
            return sql, (album["id"], limit, offset)

        # ---------- 内置相簿 ----------
        base_sql = "SELECT * FROM assets WHERE is_deleted = 0"
        params_extra = []

        if album_type == 3:  # Favorites
            base_sql = "SELECT * FROM assets WHERE is_favorite = 1 AND is_deleted = 0"
        elif album_type == 4:  # Recently Deleted
            base_sql = "SELECT * FROM assets WHERE is_deleted = 1"
        elif album_type == 5:  # All Photos
            base_sql = "SELECT * FROM assets WHERE is_deleted = 0"
        elif album_type == 6:  # Videos
            base_sql = "SELECT * FROM assets WHERE is_deleted = 0 AND mime_type LIKE 'video/%'"
        elif album_type == 7:  # Unorganized
            base_sql = """
                SELECT * FROM assets
                WHERE is_deleted = 0
                  AND id NOT IN (SELECT asset_id FROM album_assets)
            """

        # 排序（内置相簿统一用 taken_at DESC）
        order = "ORDER BY taken_at DESC"
        sql = f"{base_sql} {order} LIMIT ? OFFSET ?"
        return sql, (*params_extra, limit, offset)

    @staticmethod
    def _order_clause_for_manual(sort: str) -> str:
        if sort == "added_at":
            return "aa.added_at DESC"
        elif sort == "sort_order":
            return "aa.sort_order ASC, aa.asset_id ASC"
        else:  # 默认 taken_at
            return "aa.asset_taken_at DESC"

    # ------------------------------------------------------------------
    # 单个资产
    # ------------------------------------------------------------------
    def get_asset(self, asset_id: int) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM assets WHERE id = ?", (asset_id,)
        ).fetchone()
        return Asset(**dict(row)) if row else None

    # ------------------------------------------------------------------
    # 辅助：获取相簿封面
    # ------------------------------------------------------------------
    def get_album_cover(self, album_id: int) -> Optional[Dict[str, Any]]:
        """返回封面资产字典，若未设置则尝试取第一张资产"""
        album = self.get_album(album_id)
        if not album:
            return None
        # 1) 直接使用了 cover_asset_id
        if album["cover_asset_id"]:
            cover = self.get_asset(album["cover_asset_id"])
            if cover:
                return cover
        # 2) fallback：取相簿第一张资产
        assets = self.get_album_assets(album_id, limit=1)
        return assets[0] if assets else None
