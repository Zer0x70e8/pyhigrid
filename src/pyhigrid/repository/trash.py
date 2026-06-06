#
"""
回收站仓库 (TrashRepository)
"""

from typing import List
from .base import BaseRepository
from pyhigrid.domain.enums import BaseAlbum
from .utils.sql_helpers import placeholders


class TrashRepository(BaseRepository):
    # ---------- 资产操作 ----------
    def soft_delete_assets(self, uuids: List[str]) -> int:
        if not uuids:
            return 0
        ph = placeholders(len(uuids))
        cursor = self._execute(
            f"UPDATE assets SET is_deleted = 1 WHERE uuid IN ({ph}) AND is_deleted = 0",
            uuids
        )
        return cursor.rowcount

    def restore_assets(self, uuids: List[str]) -> int:
        if not uuids:
            return 0
        ph = placeholders(len(uuids))
        cursor = self._execute(
            f"UPDATE assets SET is_deleted = 0 WHERE uuid IN ({ph}) AND is_deleted = 1",
            uuids
        )
        return cursor.rowcount

    def permanently_delete_assets(self, uuids: List[str]) -> int:
        if not uuids:
            return 0

        with self._transaction() as conn:
            ph = placeholders(len(uuids))
            # 获取已软删除资产的内部 ID
            rows = conn.execute(
                f"SELECT id FROM assets WHERE uuid IN ({ph}) AND is_deleted = 1",
                uuids
            ).fetchall()
            asset_ids = [row["id"] for row in rows]
            if not asset_ids:
                return 0

            id_ph = placeholders(len(asset_ids))
            # 清理关联
            conn.execute(
                f"DELETE FROM album_assets WHERE asset_id IN ({id_ph})",
                asset_ids
            )
            # 永久删除资产
            cursor = conn.execute(
                f"DELETE FROM assets WHERE id IN ({id_ph})",
                asset_ids
            )
            return cursor.rowcount
        # 事务退出时自动提交，异常则回滚并记录日志

    # ---------- 相簿操作 ----------
    @staticmethod
    def _check_not_virtual(album_uuid: str):
        if BaseAlbum.from_uuid(album_uuid):
            raise ValueError("Cannot operate on system virtual albums.")

    def soft_delete_album(self, album_uuid: str) -> bool:
        self._check_not_virtual(album_uuid)
        cursor = self._execute(
            "UPDATE albums SET is_deleted = 1 WHERE uuid = ? AND is_deleted = 0",
            (album_uuid,)
        )
        return cursor.rowcount > 0

    def restore_album(self, album_uuid: str) -> bool:
        self._check_not_virtual(album_uuid)
        cursor = self._execute(
            "UPDATE albums SET is_deleted = 0 WHERE uuid = ? AND is_deleted = 1",
            (album_uuid,)
        )
        return cursor.rowcount > 0

    def permanently_delete_album(self, album_uuid: str) -> bool:
        self._check_not_virtual(album_uuid)
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT id FROM albums WHERE uuid = ? AND is_deleted = 1",
                (album_uuid,)
            ).fetchone()
            if not row:
                return False
            album_id = row["id"]
            conn.execute("DELETE FROM album_assets WHERE album_id = ?", (album_id,))
            conn.execute("DELETE FROM albums WHERE id = ?", (album_id,))
            return True
