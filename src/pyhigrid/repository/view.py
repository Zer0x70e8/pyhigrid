#
"""
视图仓库 —— 提供侧边栏/视图列表的超集。
视图包括系统内置虚拟相簿（BaseAlbum）和用户手动/智能相簿（albums表）。
每个视图返回 ViewItem 实体，包含标题、封面缩略图、资产数量等。
"""

from typing import List
from pyhigrid.domain.entities import ViewItem
from pyhigrid.domain.enums import AlbumType, BaseAlbum
from .base import BaseRepository


class ViewRepository(BaseRepository):
    """视图仓库，处理虚拟相簿和用户相簿的统一查询"""

    # ---------- 公开方法 ----------
    def get_views(self) -> List[ViewItem]:
        """获取所有视图（虚拟相簿 + 用户相簿），按约定顺序排列"""
        views = self._get_virtual_views()
        views.extend(self._get_user_albums())
        return views

    def get_view(self, view_id: str) -> ViewItem | None:
        """根据视图ID获取单个视图信息，若不存在则返回None"""
        # 先尝试虚拟相簿
        base = BaseAlbum.from_uuid(view_id)
        if base:
            return self._get_single_virtual_view(base)
        # 再尝试用户相簿
        return self._get_single_user_album(view_id)

    # ---------- 虚拟相簿 ----------
    def _get_virtual_views(self) -> List[ViewItem]:
        """生成5个系统内置虚拟相簿"""
        virtual_defs = [
            (BaseAlbum.ALL_PHOTOS, AlbumType.ALL_PHOTOS, 0),
            (BaseAlbum.UNORGANIZED, AlbumType.UNORGANIZED, 1),
            (BaseAlbum.FAVORITES, AlbumType.FAVORITES, 2),
            (BaseAlbum.RECENTLY_DELETED, AlbumType.RECENTLY_DELETED, 3),
            (BaseAlbum.VIDEOS, AlbumType.VIDEOS, 4),
        ]
        views = []
        for album, album_type, sort_order in virtual_defs:
            count = self._count_virtual_assets(album)
            cover = self._cover_for_virtual(album)
            views.append(ViewItem(
                view_id=album.value,
                title=album.label,
                view_type=album_type,
                cover_thumb=cover,
                asset_count=count,
                sort_order=sort_order,
            ))
        return views

    def _get_single_virtual_view(self, base: BaseAlbum) -> ViewItem:
        count = self._count_virtual_assets(base)
        cover = self._cover_for_virtual(base)
        sort_order = {
            BaseAlbum.ALL_PHOTOS: 0,
            BaseAlbum.UNORGANIZED: 1,
            BaseAlbum.FAVORITES: 2,
            BaseAlbum.RECENTLY_DELETED: 3,
            BaseAlbum.VIDEOS: 4,
        }[base]
        return ViewItem(
            view_id=base.value,
            title=base.label,
            view_type=base.album_type,
            cover_thumb=cover,
            asset_count=count,
            sort_order=sort_order,
        )

    def _count_virtual_assets(self, album: BaseAlbum) -> int:
        """统计虚拟相簿中的资产数量"""
        query = self._virtual_where(album, count_mode=True)
        row = self._fetchone(query)
        return row[0] if row else 0

    def _cover_for_virtual(self, album: BaseAlbum) -> str:
        """获取虚拟相簿的封面缩略图（最新一张）"""
        thumb_expr = "COALESCE(thumb_medium_path, thumb_path, thumb_small_path)"
        where = self._virtual_where(album, count_mode=False)
        # 只需where条件，拼接成完整查询
        query = f"SELECT {thumb_expr} FROM assets WHERE {where} ORDER BY taken_at DESC, created_at DESC LIMIT 1"
        row = self._fetchone(query)
        return row[0] if row and row[0] else ""

    @staticmethod
    def _virtual_where(album: BaseAlbum, count_mode: bool) -> str:
        """生成虚拟相簿的WHERE条件；count_mode返回整句'SELECT COUNT(*)...'，否则仅返回条件字符串"""
        if album == BaseAlbum.ALL_PHOTOS:
            condition = "is_deleted = 0"
        elif album == BaseAlbum.UNORGANIZED:
            condition = """
                is_deleted = 0 AND id NOT IN (
                    SELECT aa.asset_id FROM album_assets aa
                    JOIN albums al ON aa.album_id = al.id
                    WHERE al.is_deleted = 0
                )
            """
        elif album == BaseAlbum.FAVORITES:
            condition = "is_deleted = 0 AND is_favorite = 1"
        elif album == BaseAlbum.RECENTLY_DELETED:
            condition = "is_deleted = 1"
        elif album == BaseAlbum.VIDEOS:
            condition = "is_deleted = 0 AND mime_type LIKE 'video/%'"
        # else:
        #     raise ValueError(f"Unknown virtual album: {album}")

        if count_mode:
            return f"SELECT COUNT(*) FROM assets WHERE {condition}"
        return condition

    # ---------- 用户相簿 ----------
    def _get_user_albums(self) -> List[ViewItem]:
        """查询所有未删除的用户相簿（manual/smart）"""
        rows = self._fetchall(
            "SELECT id, uuid, title, album_type, cover_asset_id, sort_order "
            "FROM albums WHERE is_deleted = 0 AND album_type IN ('MANUAL', 'SMART') "
            "ORDER BY sort_order, created_at"
        )
        views = []
        for row in rows:
            album_id = row['id']
            # 资产数量
            count_row = self._fetchone(
                "SELECT COUNT(*) FROM album_assets WHERE album_id = ?", (album_id,)
            )
            count = count_row[0] if count_row else 0
            # 封面缩略图
            cover = self._album_cover(album_id, row['cover_asset_id'])
            views.append(ViewItem(
                view_id=row['uuid'],
                title=row['title'],
                view_type=AlbumType(row['album_type']),
                cover_thumb=cover,
                asset_count=count,
                sort_order=row['sort_order'],
            ))
        return views

    def _get_single_user_album(self, album_uuid: str) -> ViewItem | None:
        row = self._fetchone(
            "SELECT id, uuid, title, album_type, cover_asset_id, sort_order "
            "FROM albums WHERE uuid = ? AND is_deleted = 0", (album_uuid,)
        )
        if not row:
            return None
        album_id = row['id']
        count_row = self._fetchone(
            "SELECT COUNT(*) FROM album_assets WHERE album_id = ?", (album_id,)
        )
        count = count_row[0] if count_row else 0
        cover = self._album_cover(album_id, row['cover_asset_id'])
        return ViewItem(
            view_id=row['uuid'],
            title=row['title'],
            view_type=AlbumType(row['album_type']),
            cover_thumb=cover,
            asset_count=count,
            sort_order=row['sort_order'],
        )

    def _album_cover(self, album_id: int, cover_asset_id: int | None) -> str:
        """获取相簿封面缩略图：优先使用设定的封面，否则使用最新添加的资产"""
        if cover_asset_id:
            row = self._fetchone(
                "SELECT COALESCE(thumb_medium_path, thumb_path, thumb_small_path) "
                "FROM assets WHERE id = ?",
                (cover_asset_id,)
            )
            if row and row[0]:
                return row[0]
        # 回退：最近添加的资产
        row = self._fetchone(
            "SELECT COALESCE(a.thumb_medium_path, a.thumb_path, a.thumb_small_path) "
            "FROM assets a JOIN album_assets aa ON a.id = aa.asset_id "
            "WHERE aa.album_id = ? ORDER BY aa.added_at DESC LIMIT 1",
            (album_id,)
        )
        return row[0] if row and row[0] else ""
