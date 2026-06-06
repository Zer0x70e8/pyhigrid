#
"""
相簿仓库 (AlbumRepository)
"""

import uuid as uuid_lib
from datetime import datetime
from typing import List, Optional
from .base import BaseRepository
from pyhigrid.domain.entities import Album
from pyhigrid.domain.enums import AlbumType
from .utils.sql_helpers import placeholders, filter_dict, build_set_clause


class AlbumRepository(BaseRepository):
    ALBUM_EDITABLE_FIELDS = {"title", "cover_asset_id", "sort_order", "album_type"}

    # ---------- 相簿 CRUD ----------
    def create_album(self,
                     title: str,
                     album_type: AlbumType = AlbumType.MANUAL,
                     cover_asset_id: Optional[int] = None,
                     sort_order: int = 0) -> Album:
        album_uuid = str(uuid_lib.uuid4())
        self._execute(
            """INSERT INTO albums (uuid, title, album_type, cover_asset_id, sort_order, is_deleted)
               VALUES (?, ?, ?, ?, ?, 0)""",
            (album_uuid, title, album_type.value, cover_asset_id, sort_order)
        )
        return self.get_album(album_uuid)

    def update_album(self, album_uuid: str, **fields) -> Album:
        updates = filter_dict(fields, self.ALBUM_EDITABLE_FIELDS)
        if not updates:
            return self.get_album(album_uuid)

        set_clause, values = build_set_clause(updates)
        values.append(album_uuid)

        cursor = self._execute(
            f"UPDATE albums SET {set_clause} WHERE uuid = ? AND is_deleted = 0",
            values
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Album not found or deleted: {album_uuid}")
        return self.get_album(album_uuid)

    def get_album(self, album_uuid: str) -> Optional[Album]:
        row = self._fetchone(
            "SELECT uuid, title, album_type, cover_asset_id, sort_order, created_at, modified_at "
            "FROM albums WHERE uuid = ? AND is_deleted = 0",
            (album_uuid,)
        )
        return self._row_to_album(row) if row else None

    # ---------- 资产关联操作 ----------
    def add_assets_to_album(self, asset_uuids: List[str], album_uuid: str) -> int:
        if not asset_uuids:
            return 0

        with self._transaction() as conn:
            # 获取相簿 ID
            album_row = conn.execute(
                "SELECT id FROM albums WHERE uuid = ? AND is_deleted = 0",
                (album_uuid,)
            ).fetchone()
            if not album_row:
                raise ValueError(f"Album not found: {album_uuid}")
            album_id = album_row["id"]

            # 获取有效资产的 id 和 taken_at
            ph = placeholders(len(asset_uuids))
            asset_rows = conn.execute(
                f"SELECT id, taken_at FROM assets WHERE uuid IN ({ph}) AND is_deleted = 0",
                asset_uuids
            ).fetchall()

            inserted = 0
            for row in asset_rows:
                # noinspection PyBroadException
                try:
                    conn.execute(
                        "INSERT INTO album_assets (album_id, asset_id, asset_taken_at) VALUES (?, ?, ?)",
                        (album_id, row["id"], row["taken_at"])
                    )
                    inserted += 1
                except Exception:
                    # 主键冲突等，跳过
                    self.logger.exception(f"Failed to insert asset: {row['id']}")
            return inserted

    def remove_assets_from_album(self, asset_uuids: List[str], album_uuid: str) -> int:
        if not asset_uuids:
            return 0

        with self._transaction() as conn:
            album_row = conn.execute(
                "SELECT id FROM albums WHERE uuid = ?", (album_uuid,)
            ).fetchone()
            if not album_row:
                return 0
            album_id = album_row["id"]

            ph = placeholders(len(asset_uuids))
            asset_rows = conn.execute(
                f"SELECT id FROM assets WHERE uuid IN ({ph})",
                asset_uuids
            ).fetchall()
            asset_ids = [r["id"] for r in asset_rows]

            if not asset_ids:
                return 0

            id_ph = placeholders(len(asset_ids))
            cursor = conn.execute(
                f"DELETE FROM album_assets WHERE album_id = ? AND asset_id IN ({id_ph})",
                [album_id] + asset_ids
            )
            return cursor.rowcount

    def list_albums(self,
                    order_by: str = "sort_order",
                    order_dir: str = "ASC") -> List[Album]:
        """
        获取所有未删除的相簿列表（支持排序）。
        :param order_by: 排序字段，仅允许 title / sort_order / created_at
        :param order_dir: ASC 或 DESC
        """
        allowed_columns = {"title", "sort_order", "created_at"}
        if order_by not in allowed_columns:
            raise ValueError(f"Invalid order_by: {order_by}")
        order_dir = "ASC" if order_dir.upper() == "ASC" else "DESC"

        sql = (
            "SELECT uuid, title, album_type, cover_asset_id, sort_order, created_at, modified_at "
            "FROM albums WHERE is_deleted = 0 "
            f"ORDER BY {order_by} {order_dir}"
        )
        rows = self._fetchall(sql)
        return [self._row_to_album(r) for r in rows]

    # util
    @staticmethod
    def _row_to_album(row) -> Album:
        return Album(
            uuid=row["uuid"],
            title=row["title"],
            album_type=AlbumType(row["album_type"]),
            cover_asset_id=row["cover_asset_id"],
            sort_order=row["sort_order"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            modified_at=datetime.fromisoformat(row["modified_at"]) if row["modified_at"] else None,
        )
