#
""""""

import faulthandler  # , signal
from typing import Final

# noinspection PyUnusedImports
from pyhigrid.schemas.enums import AlbumAssetSortOption, AssetImageType

faulthandler.enable()
# signal.signal(signal.SIGSEGV, faulthandler.dump_traceback_later)


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
