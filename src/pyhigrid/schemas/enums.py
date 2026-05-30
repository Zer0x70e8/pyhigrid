# enums.py
""""""

import uuid
from enum import Enum, IntEnum

from .constants import (
    THUMB_SIZE_SMALL,
    THUMB_SIZE_MEDIUM,
    THUMB_SIZE_LARGE,

    UUID_ALL_PHOTOS,
    UUID_UNORGANIZED,
    UUID_FAVORITES,
    UUID_RECENTLY_DELETED,
    UUID_VIDEOS,
)


class AssetImageType(str, Enum):
    """
    资产图片类型枚举。
    值 = assets 表中的字段名，max_size = 生成缩略图时的长边最大像素（原图为 None）。
    """
    ORIGINAL = "file_path", None
    THUMB_LARGE = "thumb_path", THUMB_SIZE_LARGE
    THUMB_MEDIUM = "thumb_medium_path", THUMB_SIZE_MEDIUM
    THUMB_SMALL = "thumb_small_path", THUMB_SIZE_SMALL

    def __new__(cls, field: str, max_size: int | None):
        obj = str.__new__(cls, field)
        obj._value_ = field
        obj.max_size = max_size
        return obj

    @property
    def label(self) -> str:
        """前端展示标签"""
        labels = {
            AssetImageType.ORIGINAL: "original",
            AssetImageType.THUMB_LARGE: "large",
            AssetImageType.THUMB_MEDIUM: "medium",
            AssetImageType.THUMB_SMALL: "small",
        }
        return labels[self]


class AlbumAssetSortOption(str, Enum):
    TAKEN_AT = "taken_at"
    ADDED_AT = "added_at"
    SORT_ORDER = "sort_order"



# ---------- 相簿类型（对应数据库 album_type 字段） ----------
class AlbumType(IntEnum):
    """相簿类型，值与数据库 album_type 字段一致"""
    MANUAL          = 0   # 用户手动创建
    SMART           = 1   # 智能相簿（按条件自动聚合）
    FAVORITES       = 3   # 收藏
    RECENTLY_DELETED = 4  # 最近删除
    ALL_PHOTOS      = 5   # 所有照片
    VIDEOS          = 6   # 视频
    UNORGANIZED     = 7   # 未整理

    @property
    def is_virtual(self) -> bool:
        """是否属于系统内置虚拟相簿"""
        return self in (
            AlbumType.FAVORITES,
            AlbumType.RECENTLY_DELETED,
            AlbumType.ALL_PHOTOS,
            AlbumType.VIDEOS,
            AlbumType.UNORGANIZED,
        )

    def to_base_album(self):
        """如果是虚拟相簿，返回对应的 BaseAlbum 枚举，否则返回 None"""
        if not self.is_virtual:
            return None
        # 延迟引用 BaseAlbum，方法调用时 BaseAlbum 已定义
        mapping = {
            AlbumType.FAVORITES:       BaseAlbum.FAVORITES,
            AlbumType.RECENTLY_DELETED: BaseAlbum.RECENTLY_DELETED,
            AlbumType.ALL_PHOTOS:      BaseAlbum.ALL_PHOTOS,
            AlbumType.VIDEOS:          BaseAlbum.VIDEOS,
            AlbumType.UNORGANIZED:     BaseAlbum.UNORGANIZED,
        }
        return mapping[self]


# ---------- 基础（虚拟）相簿 ----------
class BaseAlbum(str, Enum):
    """
    系统内置的基础相簿，每个成员对应一个固定的 UUID。
    值 = 虚拟相簿的 UUID 字符串。
    """
    ALL_PHOTOS       = UUID_ALL_PHOTOS
    UNORGANIZED      = UUID_UNORGANIZED
    FAVORITES        = UUID_FAVORITES
    RECENTLY_DELETED = UUID_RECENTLY_DELETED
    VIDEOS           = UUID_VIDEOS

    def __new__(cls, uuid_value: uuid.UUID):
        obj = str.__new__(cls, str(uuid_value))
        obj._value_ = str(uuid_value)
        obj.uuid = uuid_value
        return obj

    @property
    def label(self) -> str:
        labels = {
            BaseAlbum.ALL_PHOTOS:       "所有照片",
            BaseAlbum.UNORGANIZED:      "未整理",
            BaseAlbum.FAVORITES:        "收藏",
            BaseAlbum.RECENTLY_DELETED: "最近删除",
            BaseAlbum.VIDEOS:           "视频",
        }
        return labels[self]

    @property
    def album_type(self) -> AlbumType:
        """对应的 AlbumType 枚举值"""
        mapping = {
            BaseAlbum.ALL_PHOTOS:       AlbumType.ALL_PHOTOS,
            BaseAlbum.UNORGANIZED:      AlbumType.UNORGANIZED,
            BaseAlbum.FAVORITES:        AlbumType.FAVORITES,
            BaseAlbum.RECENTLY_DELETED: AlbumType.RECENTLY_DELETED,
            BaseAlbum.VIDEOS:           AlbumType.VIDEOS,
        }
        return mapping[self]

    @classmethod
    def from_uuid(cls, value: uuid.UUID | str) -> "BaseAlbum | None":
        if isinstance(value, uuid.UUID):
            value = str(value)
        for member in cls:
            if member.value == value:
                return member
        return None

    @classmethod
    def is_base_album(cls, album_id: uuid.UUID | str) -> bool:
        return cls.from_uuid(album_id) is not None
