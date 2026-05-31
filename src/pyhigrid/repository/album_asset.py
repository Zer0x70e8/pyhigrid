#
""""""

from typing import Optional, List, Tuple
from sqlite3 import Row

from .base import BaseRepository


class AlbumAssetRepo(BaseRepository):
    """相簿资产关联仓库，负责 album_assets 表及关联资产的基本查询。"""

    # ---------- 增删关联 ----------
    def add_asset_to_album(
        self,
        album_id: int,
        asset_id: int,
        sort_order: int = 0,
        asset_taken_at: Optional[str] = None,
    ) -> None:
        """添加资产到相簿，重复添加会被忽略。"""
        query = """
            INSERT OR IGNORE INTO album_assets (album_id, asset_id, asset_taken_at, sort_order)
            VALUES (?, ?, ?, ?)
        """
        self._execute(query, (album_id, asset_id, asset_taken_at, sort_order))

    def remove_asset_from_album(self, album_id: int, asset_id: int) -> None:
        """从相簿移除单个资产。"""
        query = "DELETE FROM album_assets WHERE album_id = ? AND asset_id = ?"
        self._execute(query, (album_id, asset_id))

    def bulk_add_assets_to_album(
        self,
        album_id: int,
        asset_ids: List[int],
        default_sort_order: int = 0,
    ) -> None:
        """批量添加资产，忽略已存在的关联。"""
        query = """
            INSERT OR IGNORE INTO album_assets (album_id, asset_id, sort_order)
            VALUES (?, ?, ?)
        """
        params = [(album_id, aid, default_sort_order) for aid in asset_ids]
        with self._db.connect() as conn:
            conn.executemany(query, params)
            conn.commit()

    def bulk_remove_assets_from_album(self, album_id: int, asset_ids: List[int]) -> None:
        """批量移除资产。"""
        if not asset_ids:
            return
        placeholders = ",".join("?" for _ in asset_ids)
        query = f"DELETE FROM album_assets WHERE album_id = ? AND asset_id IN ({placeholders})"
        self._execute(query, [album_id] + asset_ids)

    # ---------- 更新关联属性 ----------
    def update_asset_in_album(
        self,
        album_id: int,
        asset_id: int,
        sort_order: Optional[int] = None,
        asset_taken_at: Optional[str] = None,
    ) -> None:
        """更新单个资产在相簿中的排序或拍摄时间。"""
        updates = []
        params = []
        if sort_order is not None:
            updates.append("sort_order = ?")
            params.append(sort_order)
        if asset_taken_at is not None:
            updates.append("asset_taken_at = ?")
            params.append(asset_taken_at)
        if not updates:
            return
        params.extend([album_id, asset_id])
        query = f"UPDATE album_assets SET {', '.join(updates)} WHERE album_id = ? AND asset_id = ?"
        self._execute(query, params)

    def reorder_assets_in_album(
        self, album_id: int, order_list: List[Tuple[int, int]]
    ) -> None:
        """
        批量更新资产排序。
        order_list: [(asset_id, new_sort_order), ...]
        """
        if not order_list:
            return
        # 构建 CASE WHEN 语句
        cases = " ".join(
            f"WHEN asset_id = ? THEN ?" for _ in order_list
        )
        asset_ids = [aid for aid, _ in order_list]
        new_orders = [order for _, order in order_list]
        placeholders = ",".join("?" for _ in asset_ids)

        query = f"""
            UPDATE album_assets
            SET sort_order = CASE {cases} END
            WHERE album_id = ? AND asset_id IN ({placeholders})
        """
        params = []
        for aid, order in order_list:
            params.append(aid)
            params.append(order)
        params.append(album_id)
        params.extend(asset_ids)
        self._execute(query, params)

    # ---------- 查询 ----------
    def get_assets_in_album(
        self,
        album_id: int,
        order_by: str = "added_at",
        order_dir: str = "desc",
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Row]:
        """
        获取相簿内的资产列表（自动排除已软删除的资产及相簿本身已删除）。
        排序字段: added_at, sort_order, asset_taken_at
        """
        allowed_order = {"added_at", "sort_order", "asset_taken_at"}
        if order_by not in allowed_order:
            raise ValueError(f"Invalid order_by: {order_by}")
        direction = "DESC" if order_dir.lower() == "desc" else "ASC"

        query = """
            SELECT a.*
            FROM assets a
            JOIN album_assets aa ON a.id = aa.asset_id
            JOIN albums al ON aa.album_id = al.id
            WHERE aa.album_id = ?
              AND a.is_deleted = 0
              AND al.is_deleted = 0
        """
        params = [album_id]

        query += f" ORDER BY aa.{order_by} {direction}"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        query += " OFFSET ?"
        params.append(offset)

        return self._fetchall(query, params) or []

    def get_asset_count_in_album(self, album_id: int) -> int:
        """获取相簿内有效资产数量。"""
        query = """
            SELECT COUNT(*)
            FROM album_assets aa
            JOIN assets a ON aa.asset_id = a.id
            JOIN albums al ON aa.album_id = al.id
            WHERE aa.album_id = ?
              AND a.is_deleted = 0
              AND al.is_deleted = 0
        """
        row = self._fetchone(query, (album_id,))
        return row[0] if row else 0

    def get_albums_for_asset(self, asset_id: int) -> List[Row]:
        """获取包含指定资产的所有未删除相簿。"""
        query = """
            SELECT al.*
            FROM albums al
            JOIN album_assets aa ON al.id = aa.album_id
            WHERE aa.asset_id = ?
              AND al.is_deleted = 0
        """
        return self._fetchall(query, (asset_id,)) or []

    def is_asset_in_album(self, album_id: int, asset_id: int) -> bool:
        """检查资产是否已存在于指定相簿。"""
        query = "SELECT 1 FROM album_assets WHERE album_id = ? AND asset_id = ? LIMIT 1"
        row = self._fetchone(query, (album_id, asset_id))
        return row is not None
