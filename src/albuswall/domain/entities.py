# entities.py
""""""

from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Optional, List, Dict, Any

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
    source_id: Optional[int] = None

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
    source_id: Optional[int] = None

@dataclass
class AssetDetail:
    """资产详情面板展示实体"""
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
    source_id: str


@dataclass
class IngestSourceEntity:
    id: Optional[int] = None
    title: str = ""
    source_path: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    file_types: List[str] = field(default_factory=list)
    file_type_check: str = "suffix"
    subfolder_recursion: bool = False
    subfolder_recursion_depth: Optional[int] = None
    target_path: str = ""  # 注意：这里是 target_path，不是 target
    auto_mount: bool = False
    mount_point: str = ""
    # 以下字段来自 trigger_config
    update_mode: str = "scheduled_time"
    device_trigger_enabled: bool = False
    scheduled_enabled: bool = False
    scheduled_time: str = ""
    interval_time: str = ""
    created_at: Optional[str] = None
    modified_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IngestSourceEntity":
        valid_fields = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source_path": self.source_path,
            "description": self.description,
            "tags": self.tags,
            "file_types": self.file_types,
            "file_type_check": self.file_type_check,
            "subfolder_recursion": self.subfolder_recursion,
            "subfolder_recursion_depth": self.subfolder_recursion_depth,
            "target_path": self.target_path,
            "auto_mount": self.auto_mount,
            "mount_point": self.mount_point,
            "update_mode": self.update_mode,
            "device_trigger_enabled": self.device_trigger_enabled,
            "scheduled_enabled": self.scheduled_enabled,
            "scheduled_time": self.scheduled_time,
            "interval_time": self.interval_time,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }

    # 将 trigger_config 字典的内容填充到实体字段
    def apply_trigger_config(self, config: Optional[Dict[str, Any]]) -> None:
        if not config:
            return
        self.update_mode = config.get("update_mode", self.update_mode)
        device_trigger = config.get("device_trigger", {})
        self.device_trigger_enabled = device_trigger.get("enabled", False)
        scheduled = config.get("scheduled", {})
        self.scheduled_enabled = scheduled.get("enabled", False)
        self.scheduled_time = scheduled.get("time", "")
        self.interval_time = scheduled.get("interval", "")

    # 从实体字段构建 trigger_config 字典
    def build_trigger_config(self) -> Dict[str, Any]:
        return {
            "update_mode": self.update_mode,
            "device_trigger": {
                "enabled": self.device_trigger_enabled
            },
            "scheduled": {
                "enabled": self.scheduled_enabled,
                "time": self.scheduled_time or None,
                "interval": self.interval_time or None,
            }
        }
