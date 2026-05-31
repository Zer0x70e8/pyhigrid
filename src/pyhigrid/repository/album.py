#
""""""

import uuid
from typing import Optional, List
from sqlite3 import Row

from .base import BaseRepository


class AlbumRepo(BaseRepository):
    """相簿仓库：仅负责 albums 表操作，软删除为异步标记，不提供恢复。"""

    def create_album(
        self,
        title: str,
        album_type: int = 0,
        cover_asset_id: Optional[int] = None,
        sort_order: int = 0,
    ) -> Row:
        """创建相簿并返回完整记录。"""
        album_uuid = str(uuid.uuid4())
        query = """
            INSERT INTO albums (uuid, title, album_type, cover_asset_id, sort_order)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor = self._execute(query, (album_uuid, title, album_type, cover_asset_id, sort_order))
        return self.get_album_by_id(cursor.lastrowid)

    def get_album_by_id(self, album_id: int, include_deleted: bool = False) -> Optional[Row]:
        """根据主键获取相簿，可选择是否包含已标记删除的相簿。"""
        query = "SELECT * FROM albums WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        return self._fetchone(query, (album_id,))

    def get_album_by_uuid(self, uuid_str: str, include_deleted: bool = False) -> Optional[Row]:
        """根据 UUID 获取相簿。"""
        query = "SELECT * FROM albums WHERE uuid = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        return self._fetchone(query, (uuid_str,))

    def get_all_albums(
        self,
        include_deleted: bool = False,
        order_by: str = "created_at",
        order_dir: str = "desc",
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Row]:
        """
        获取相簿列表，支持排序与分页。
        order_by 仅允许: created_at, modified_at, title, sort_order
        """
        allowed_columns = {"created_at", "modified_at", "title", "sort_order"}
        if order_by not in allowed_columns:
            raise ValueError(f"Invalid order_by: {order_by}")
        order_dir = "DESC" if order_dir.lower() == "desc" else "ASC"

        query = "SELECT * FROM albums"
        params = []
        if not include_deleted:
            query += " WHERE is_deleted = 0"
        query += f" ORDER BY {order_by} {order_dir}"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        query += " OFFSET ?"
        params.append(offset)

        return self._fetchall(query, params) or []

    def update_album(self, album_id: int, **fields) -> Optional[Row]:
        """
        更新相簿字段（title, album_type, cover_asset_id, sort_order）。
        支持将 cover_asset_id 显式设为 None。
        """
        allowed = {"title", "album_type", "cover_asset_id", "sort_order"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_album_by_id(album_id)

        set_clause = ", ".join(f"{col} = ?" for col in updates)
        params = list(updates.values())
        params.append(album_id)

        query = f"UPDATE albums SET {set_clause}, modified_at = strftime('%Y-%m-%dT%H:%M:%f','now') WHERE id = ?"
        self._execute(query, params)
        return self.get_album_by_id(album_id)

    def mark_album_deleted(self, album_id: int) -> None:
        """标记相簿为已删除（供后台任务处理），不物理删除。"""
        query = """
            UPDATE albums
            SET is_deleted = 1,
                deleted_at = strftime('%Y-%m-%dT%H:%M:%f','now'),
                modified_at = strftime('%Y-%m-%dT%H:%M:%f','now')
            WHERE id = ? AND is_deleted = 0
        """
        self._execute(query, (album_id,))

    def set_cover(self, album_id: int, asset_id: int) -> Optional[Row]:
        """设置相簿封面资产。"""
        return self.update_album(album_id, cover_asset_id=asset_id)

    def count_albums(self, include_deleted: bool = False) -> int:
        """统计相簿数量。"""
        query = "SELECT COUNT(*) FROM albums"
        if not include_deleted:
            query += " WHERE is_deleted = 0"
        row = self._fetchone(query)
        return row[0] if row else 0
