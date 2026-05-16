#
"""
Virtual scrolling widget for displaying a grid of images (or placeholders) asynchronously.

This module provides a `VirtualScrolledWidget` that supports smooth pixel-level scrolling over
a virtually infinite list of items, rendered in a grid layout. Each item is represented by a `Cell`
(QLabel) that loads its content asynchronously via a thread pool and a user-provided image provider
function. The widget reuses `Cell` objects to minimise memory usage and only manages those currently
visible in the viewport.
"""

import faulthandler  # , signal
from typing import Final, TYPE_CHECKING

# noinspection PyUnusedImports
from pyhigrid.schemas.enums import AlbumAssetSortOption, AssetImageType

faulthandler.enable()
# signal.signal(signal.SIGSEGV, faulthandler.dump_traceback_later)

if TYPE_CHECKING:
    __doc__ = __doc__

__all__ = [
    "__doc__",
    "AlbumAssetSortOption", "AssetImageType",
    "WHEEL_INVERTED", "ZOOM_WHEEL_INVERTED",
    "TOTAL_CONTENT_HEIGHT", "CACHE_POOL_MAX_ITEM_NUMBER",
    "DEFAULT_COLUMN_COUNT", "OVERSCROLL_TOP_MAX", "MAX_ITEM_INDEX",
    "SCROLL_LINE_FRACTION", "FALLBACK_CELL_SIZE", "WHEEL_DELTA_BASE",
    # "CORNER_RADIUS",
    "WHEEL_PIXEL_STEP",
    # "ENABLE_PERCENTAGE_BASED_CELL_ROW_SCROLLING", "PERCENTAGE_BASED_CELL_ROW_SCROLLING_STEP",
]


WHEEL_INVERTED: Final[bool] = False
ZOOM_WHEEL_INVERTED: Final[bool] = False

TOTAL_CONTENT_HEIGHT: Final[int] = 0
CACHE_POOL_MAX_ITEM_NUMBER: Final[int] = 20
DEFAULT_COLUMN_COUNT: Final[int] = 5
OVERSCROLL_TOP_MAX: Final[int] = 0
MAX_ITEM_INDEX: Final[int] = 1_000_000  # use for test
SCROLL_LINE_FRACTION: Final[int] = 10  # 无参数时滚动距离为视口高度的 1/N（这里 N=10）
FALLBACK_CELL_SIZE: Final[int] = 100  # 当控件宽度无效时的单元格大小回退值
WHEEL_DELTA_BASE: Final[int] = 120  # Qt 鼠标滚轮标准  # 极少需要改

# CORNER_RADIUS: Final[int] = 8

WHEEL_PIXEL_STEP: Final[int] = 30
# ENABLE_PERCENTAGE_BASED_CELL_ROW_SCROLLING: Final[bool] = False
# PERCENTAGE_BASED_CELL_ROW_SCROLLING_STEP: Final[float] = 0.5  # 每次滚动半个单元格高度
