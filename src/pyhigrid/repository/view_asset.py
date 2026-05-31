#
"""
视图资产仓库 —— 以视图为单位获取资产列表和资产详情。
查询时先识别视图类型（虚拟相簿或用户相簿），再拼装相应的筛选语句。
"""

import json
from typing import List, Optional
from pyhigrid.domain.entities import AssetItem, AssetDetail
from pyhigrid.domain.enums import BaseAlbum, AlbumAssetSortOption
from .base import BaseRepository


class ViewAssetRepository(BaseRepository):
    """资产查询仓库，所有查询必须以视图(view_id)为入口"""

    # ---------- 资产列表 ----------
    def get_assets(self,
                   view_id: str,
                   sort_by: AlbumAssetSortOption = AlbumAssetSortOption.TAKEN_AT,
                   offset: int = 0,
                   limit: int = 50) -> List[AssetItem]:
        """
        获取指定视图下的资产列表，支持排序和分页。
        :param view_id: 视图ID（虚拟相簿UUID或用户相簿UUID）
        :param sort_by:  排序字段枚举
        :param offset:   分页偏移
        :param limit:    每页数量
        """
        base_album = BaseAlbum.from_uuid(view_id)
        if base_album:
            return self._query_virtual_assets(base_album, sort_by, offset, limit)
        return self._query_album_assets(view_id, sort_by, offset, limit)

    def _query_virtual_assets(self,
                              base_album: BaseAlbum,
                              sort_by: AlbumAssetSortOption,
                              offset: int,
                              limit: int) -> List[AssetItem]:
        """查询虚拟相簿的资产"""
        where, order = self._virtual_clauses(base_album, sort_by)
        query = f"""
            SELECT
                uuid,
                COALESCE(thumb_medium_path, thumb_path, thumb_small_path) AS thumb_path,
                taken_at,
                mime_type,
                is_favorite
            FROM assets
            WHERE {where}
            ORDER BY {order}
            LIMIT ? OFFSET ?
        """
        rows = self._fetchall(query, (limit, offset))
        return [self._row_to_asset_item(row) for row in rows]

    def _query_album_assets(self,
                            album_uuid: str,
                            sort_by: AlbumAssetSortOption,
                            offset: int,
                            limit: int) -> List[AssetItem]:
        """查询用户相簿的资产（通过album_assets关联）"""
        # 先获取album_id
        album_row = self._fetchone(
            "SELECT id FROM albums WHERE uuid = ? AND is_deleted = 0",
            (album_uuid,)
        )
        if not album_row:
            return []
        album_id = album_row['id']

        order_field = {
            AlbumAssetSortOption.TAKEN_AT: "aa.asset_taken_at",
            AlbumAssetSortOption.ADDED_AT: "aa.added_at",
            AlbumAssetSortOption.SORT_ORDER: "aa.sort_order",
        }.get(sort_by, "aa.added_at")

        query = f"""
            SELECT
                a.uuid,
                COALESCE(a.thumb_medium_path, a.thumb_path, a.thumb_small_path) AS thumb_path,
                a.taken_at,
                a.mime_type,
                a.is_favorite
            FROM assets a
            JOIN album_assets aa ON a.id = aa.asset_id
            WHERE aa.album_id = ? AND a.is_deleted = 0
            ORDER BY {order_field} DESC
            LIMIT ? OFFSET ?
        """
        rows = self._fetchall(query, (album_id, limit, offset))
        return [self._row_to_asset_item(row) for row in rows]

    @staticmethod
    def _virtual_clauses(base_album: BaseAlbum, sort_by: AlbumAssetSortOption):
        """返回虚拟相簿的WHERE条件和ORDER子句"""
        if base_album == BaseAlbum.ALL_PHOTOS:
            where = "is_deleted = 0"
        elif base_album == BaseAlbum.UNORGANIZED:
            where = """
                is_deleted = 0 AND id NOT IN (
                    SELECT aa.asset_id FROM album_assets aa
                    JOIN albums al ON aa.album_id = al.id
                    WHERE al.is_deleted = 0
                )
            """
        elif base_album == BaseAlbum.FAVORITES:
            where = "is_deleted = 0 AND is_favorite = 1"
        elif base_album == BaseAlbum.RECENTLY_DELETED:
            where = "is_deleted = 1"
        elif base_album == BaseAlbum.VIDEOS:
            where = "is_deleted = 0 AND mime_type LIKE 'video/%'"
        # else:
        #     raise ValueError(f"Unknown virtual album: {base_album}")

        # 虚拟相簿没有album_assets的冗余字段，映射回assets表字段
        order_field = {
            AlbumAssetSortOption.TAKEN_AT: "taken_at",
            AlbumAssetSortOption.ADDED_AT: "created_at",
            AlbumAssetSortOption.SORT_ORDER: "taken_at",  # 降级
        }.get(sort_by, "taken_at")

        return where, f"{order_field} DESC"

    @staticmethod
    def _row_to_asset_item(row) -> AssetItem:
        """将sqlite3.Row转换为AssetItem"""
        mime = row['mime_type'] or ""
        media_type = 'video' if mime.startswith('video/') else 'image'
        return AssetItem(
            uuid=row['uuid'],
            thumb_path=row['thumb_path'] or "",
            taken_at=row['taken_at'],
            media_type=media_type,
            duration=None,      # 暂不存储视频时长
            is_favorite=bool(row['is_favorite']),
        )

    # ---------- 资产详情 ----------
    def get_asset_detail(self, asset_uuid: str) -> Optional[AssetDetail]:
        """获取单个资产详情，包含从exif_json中提取的拍摄参数"""
        row = self._fetchone(
            "SELECT * FROM assets WHERE uuid = ?", (asset_uuid,)
        )
        if not row:
            return None

        exif = {}
        if row['exif_json']:
            try:
                exif = json.loads(row['exif_json'])
            except (json.JSONDecodeError, TypeError):
                pass

        return AssetDetail(
            uuid=row['uuid'],
            file_name=row['original_name'],
            file_path=row['file_path'],
            file_size=row['file_size'],
            width=row['width'],
            height=row['height'],
            mime_type=row['mime_type'],
            taken_at=row['taken_at'],
            camera_model=exif.get('Model') or exif.get('camera_model'),
            exposure_time=exif.get('ExposureTime') or exif.get('exposure_time'),
            f_number=exif.get('FNumber') or exif.get('f_number'),
            iso=exif.get('ISOSpeedRatings') or exif.get('iso'),
            focal_length=exif.get('FocalLength') or exif.get('focal_length'),
            gps_latitude=exif.get('GPSLatitude') or exif.get('gps_latitude'),
            gps_longitude=exif.get('GPSLongitude') or exif.get('gps_longitude'),
            created_at=row['created_at'],
            modified_at=row['modified_at'],
        )
