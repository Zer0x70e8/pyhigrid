#
""""""

from typing import List
from .base import BaseRepository
from albuswall.domain.enums import BaseAlbum
from .utils.sql_helpers import placeholders


class TrashRepository(BaseRepository):
    """回收站仓库，负责资产的软删除、恢复和永久删除，以及相簿的类似操作。"""

    # ---------- 资产操作 ----------
    def soft_delete_assets(self, uuids: List[str]) -> int:
        """
        软删除多个资产：设置 is_deleted=1 并记录删除时间。
        返回受影响的行数（实际被标记删除的资产数量）。
        """
        if not uuids:
            return 0
        # 过滤掉空字符串或 None，避免无效参数
        valid_uuids = [u for u in uuids if u]
        if not valid_uuids:
            return 0

        ph = placeholders(len(valid_uuids))
        cursor = self._execute(
            f"""
            UPDATE assets 
            SET is_deleted = 1, 
                deleted_at = strftime('%Y-%m-%dT%H:%M:%f', 'now') 
            WHERE uuid IN ({ph}) AND is_deleted = 0
            """,
            valid_uuids
        )
        return cursor.rowcount

    def restore_assets(self, uuids: List[str]) -> int:
        """
        恢复多个已软删除的资产：设置 is_deleted=0 并清空删除时间。
        返回受影响的行数。
        """
        if not uuids:
            return 0
        valid_uuids = [u for u in uuids if u]
        if not valid_uuids:
            return 0

        ph = placeholders(len(valid_uuids))
        cursor = self._execute(
            f"""
            UPDATE assets 
            SET is_deleted = 0, deleted_at = NULL 
            WHERE uuid IN ({ph}) AND is_deleted = 1
            """,
            valid_uuids
        )
        return cursor.rowcount

    def permanently_delete_assets(self, uuids: List[str]) -> int:
        """
        永久删除多个已软删除的资产及其关联记录。
        使用事务确保数据一致性。
        返回永久删除的资产数量。
        """
        if not uuids:
            return 0
        valid_uuids = [u for u in uuids if u]
        if not valid_uuids:
            return 0

        with self._transaction() as conn:
            ph = placeholders(len(valid_uuids))
            # 获取已软删除资产的内部 ID
            rows = conn.execute(
                f"""
                SELECT id FROM assets 
                WHERE uuid IN ({ph}) AND is_deleted = 1
                """,
                valid_uuids
            ).fetchall()
            asset_ids = [row["id"] for row in rows]
            if not asset_ids:
                return 0

            id_ph = placeholders(len(asset_ids))
            # 清理关联（相簿-资产关系）
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
        # 事务退出时自动提交；若发生异常，则回滚并记录日志（由基类处理）

    # ---------- 相簿操作 ----------
    @staticmethod
    def _check_not_virtual(album_uuid: str):
        """
        检查相簿是否为系统虚拟相簿。
        虚拟相簿（如“所有照片”“回收站”等）不允许删除或修改。
        """
        if BaseAlbum.from_uuid(album_uuid):
            raise ValueError("Cannot operate on system virtual albums.")

    def soft_delete_album(self, album_uuid: str) -> bool:
        """
        软删除一个相簿（不删除其中的资产）。
        返回是否成功。
        """
        self._check_not_virtual(album_uuid)
        cursor = self._execute(
            "UPDATE albums SET is_deleted = 1 WHERE uuid = ? AND is_deleted = 0",
            (album_uuid,)
        )
        return cursor.rowcount > 0

    def restore_album(self, album_uuid: str) -> bool:
        """
        恢复一个已软删除的相簿。
        返回是否成功。
        """
        self._check_not_virtual(album_uuid)
        cursor = self._execute(
            "UPDATE albums SET is_deleted = 0 WHERE uuid = ? AND is_deleted = 1",
            (album_uuid,)
        )
        return cursor.rowcount > 0

    def permanently_delete_album(self, album_uuid: str) -> bool:
        """
        永久删除一个已软删除的相簿，并清理其关联关系（不删除资产）。
        返回是否成功。
        """
        self._check_not_virtual(album_uuid)
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT id FROM albums WHERE uuid = ? AND is_deleted = 1",
                (album_uuid,)
            ).fetchone()
            if not row:
                return False
            album_id = row["id"]
            # 删除相簿与资产的关联
            conn.execute("DELETE FROM album_assets WHERE album_id = ?", (album_id,))
            # 删除相簿记录
            conn.execute("DELETE FROM albums WHERE id = ?", (album_id,))
            return True
