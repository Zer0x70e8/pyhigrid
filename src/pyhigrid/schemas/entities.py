#
""""""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Asset:
    id: int
    uuid: str
    file_path: str
    thumb_path: Optional[str]
    thumb_small_path: Optional[str]
    thumb_medium_path: Optional[str]
    original_name: str
    mime_type: str
    file_hash: str
    file_size: int
    width: int
    height: int
    taken_at: str  # ISO 格式，也可考虑 datetime
    city: Optional[str]
    exif_json: Optional[str]
    is_favorite: bool = False
    is_deleted: bool = False
    deleted_at: Optional[str] = None
    created_at: Optional[str] = None
    modified_at: Optional[str] = None

    # 可以不映射所有字段，但保持与 assets 表一致


@dataclass
class Album:
    id: int
    uuid: str
    title: str
    album_type: int  # 0:手动 1:智能 3:收藏 4:最近删除 5:所有照片 6:视频 7:未整理
    cover_asset_id: Optional[int] = None
    sort_order: int = 0
    is_deleted: bool = False
    # 可补充 created_at / modified_at 等


@dataclass
class AlbumAsset:
    album_id: int
    asset_id: int
    asset_taken_at: Optional[str] = None
    added_at: Optional[str] = None
    sort_order: int = 0
