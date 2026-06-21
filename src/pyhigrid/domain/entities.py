# entities.py
""""""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .enums import AlbumType


# @dataclass
# class Asset:
#     id: int
#     uuid: str
#     file_path: str
#     thumb_path: Optional[str]
#     thumb_small_path: Optional[str]
#     thumb_medium_path: Optional[str]
#     original_name: str
#     mime_type: str
#     file_hash: str
#     file_size: int
#     width: int
#     height: int
#     taken_at: str  # ISO 格式
#     city: Optional[str]
#     exif_json: Optional[str]
#     is_favorite: bool = False
#     is_deleted: bool = False
#     deleted_at: Optional[str] = None
#     created_at: Optional[str] = None
#     modified_at: Optional[str] = None
#
#     # 可以不映射所有字段，但保持与 assets 表一致


@dataclass
class Album:
    uuid: str
    title: str
    album_type: AlbumType  # 0:手动 1:智能 3:收藏 4:最近删除 5:所有照片 6:视频 7:未整理
    cover_asset_id: Optional[int] = None
    sort_order: int = 0
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None


# @dataclass
# class AlbumAsset:
#     album_id: int
#     asset_id: int
#     asset_taken_at: Optional[str] = None
#     added_at: Optional[str] = None
#     sort_order: int = 0


@dataclass
class FileImportInfo:
    """封装一个待导入文件的原始信息，避免服务层直接拼装 Asset"""
    uuid: str
    file_path: str
    original_name: str
    mime_type: str
    file_hash: str
    file_size: int
    width: int
    height: int
    taken_at: Optional[str] = None
    city: Optional[str] = None
    exif_json: Optional[str] = None
    thumb_path: Optional[str] = None
    thumb_small_path: Optional[str] = None
    thumb_medium_path: Optional[str] = None
    is_favorite: bool = False

    # 如果未来需要标签，可以暂时添加一个列表，但数据库未支持标签表，仅做预留
    # tags: List[str] = field(default_factory=list)

@dataclass
class ViewItem:
    """视图列表/侧边栏展示实体"""
    view_id: str           # BaseAlbum.value 或相簿 uuid
    title: str
    view_type: AlbumType
    cover_thumb: str       # 必选，无资产时用默认图（前端处理）
    asset_count: int
    sort_order: int

@dataclass
class AssetItem:
    """资产网格/瀑布流展示实体"""
    uuid: str
    file_path: str
    taken_at: Optional[str]    # ISO 格式日期
    media_type: str            # 'image' 或 'video'
    duration: Optional[float]  # 视频时长
    is_favorite: bool

@dataclass
class AssetDetail:
    """资产详情面板展示实体（按需）"""
    uuid: str
    file_name: str
    file_path: str
    file_size: int
    width: int
    height: int
    mime_type: str
    taken_at: Optional[str]
    camera_model: Optional[str]
    exposure_time: Optional[str]
    f_number: Optional[str]
    iso: Optional[int]
    focal_length: Optional[str]
    gps_latitude: Optional[float]
    gps_longitude: Optional[float]
    created_at: str
    modified_at: str
