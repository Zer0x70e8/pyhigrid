# enums.py
""""""

from enum import Enum

from .constants import THUMB_SIZE_SMALL, THUMB_SIZE_MEDIUM, THUMB_SIZE_LARGE


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
