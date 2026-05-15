#
""""""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ThumbSize(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


@dataclass
class AlbumInfo:
    album_id: int
    title: str
    asset_count: int
    first_uuid: Optional[str]  # 第一张资产的 UUID，相簿为空则为 None


@dataclass
class AssetThumbData:
    """每条资产在滚动列表中的轻量描述，只保留缩略图所需信息"""
    uuid: str
    # 三种尺寸的缩略图文件路径，来自 Asset 实体的对应字段
    thumb_small: Optional[str]
    thumb_medium: Optional[str]
    thumb_large: Optional[str]
    original_path: Optional[str]  # 原图路径，用以回退生成缩略图（若预生成缺失）
