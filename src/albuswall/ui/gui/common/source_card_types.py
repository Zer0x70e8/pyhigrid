#
""""""

from typing import TypedDict, Union
from PySide6.QtGui import QFont, QColor


class FontConfig(TypedDict, total=False):
    family: str
    size: int
    weight: int          # QFont.Weight
    italic: bool


class TextStyleConfig(TypedDict, total=False):
    """文本元素（标题、路径、描述）的样式"""
    font: Union[FontConfig, QFont]
    color: Union[str, QColor]              # 普通状态文字颜色
    selected_color: Union[str, QColor]     # 选中状态文字颜色


class TagStyleConfig(TypedDict, total=False):
    """标签元素的样式"""
    font: Union[FontConfig, QFont]
    text_color: Union[str, QColor]
    selected_text_color: Union[str, QColor]
    background_color: Union[str, QColor]
    selected_background_color: Union[str, QColor]


class SourceCardStyleConfig(TypedDict, total=False):
    card_margin: int
    card_padding: int
    title: TextStyleConfig
    path: TextStyleConfig
    desc: TextStyleConfig
    tags: TagStyleConfig
