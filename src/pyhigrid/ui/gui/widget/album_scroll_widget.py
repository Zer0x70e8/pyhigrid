#
""""""

import faulthandler  # , signal

import os
from collections import OrderedDict
from typing import Final, Callable, Set, Optional, List, Dict

from PySide6.QtGui import QImage, QPixmap, QPainter, QFont, QColor, QImageReader, QPainterPath
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, Signal, QThreadPool, Slot, QObject, QRunnable, QMutex, QMutexLocker, QSize

from pyhigrid.schemas.enums import AlbumAssetSortOption, AssetImageType

faulthandler.enable()
# signal.signal(signal.SIGSEGV, faulthandler.dump_traceback_later)


WHEEL_INVERTED: Final[bool] = False

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


def image_provider(number, size=256) -> QImage:
    """
    Generate a placeholder QImage for a given number.
    This function is designed to be executed in a worker thread because it only operates on QImage,
    which is safe to use in a non-GUI thread in Qt5+ when painting on a QImage with
    QPainter (QImage is a paint device with a render target).

    Args:
        number: The numeric value to display in the centre of the image.
        size: Side length of the square image. Defaults to 256.

    Returns:
        A QImage filled with white and centred black text of the given number.
    """
    # This function runs in a worker thread; only touch QImage, no GUI widgets.
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.white)
    # Painting on a QImage that has a render target is thread-safe (Qt5+).
    # noinspection SpellCheckingInspection
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    font = QFont("Arial", size // 4)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("black"))
    if isinstance(number, float):
        if number.is_integer():
            text = str(int(number))
        else:
            text = f"{number:.2f}"
    else:
        text = str(number)
    painter.drawText(img.rect(), Qt.AlignCenter, text)
    painter.end()
    return img


# ---------- 离屏圆角生成 ----------
def make_rounded_image(source: QImage, target_size: QSize, radius: int) -> QImage:
    """将源图缩放、居中裁剪到 target_size，并加上圆角，返回 ARGB32 图片。"""
    if source.isNull() or target_size.isEmpty():
        return QImage()

    # 1. 缩放（保持比例，填满目标尺寸）
    scaled = source.scaled(
        target_size,
        Qt.KeepAspectRatioByExpanding,
        Qt.SmoothTransformation,
    )

    # 2. 居中裁剪
    x = (scaled.width() - target_size.width()) // 2
    y = (scaled.height() - target_size.height()) // 2
    cropped = scaled.copy(x, y, target_size.width(), target_size.height())

    # 3. 创建透明目标图，绘制圆角路径
    result = QImage(target_size, QImage.Format_ARGB32_Premultiplied)
    result.fill(Qt.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(
        0, 0, target_size.width(), target_size.height(), radius, radius
    )
    painter.setClipPath(path)
    painter.drawImage(0, 0, cropped)
    painter.end()

    return result


class ImageLoadTaskSignals(QObject):
    """Signals for the image loading task."""
    finished = Signal(object, object)  # number, QImage


class ImageLoadTask(QRunnable):
    """
    Worker task that calls the image provider function and emits the result.
    The task is executed in a thread pool to avoid blocking the GUI thread.
    """

    def __init__(self, number, func):
        """
        Args:
            number: The index/number that will be passed to the image generator.
            func: A callable that accepts a number and returns a QImage.
        """
        super().__init__()
        self.number = number
        self.func = func
        self._signals = ImageLoadTaskSignals()

    @property
    def signals(self):
        return self._signals

    def run(self):
        """Execute the image generation and emit the result via signal."""
        # func returns QImage (safe for cross-thread signals)
        image = self.func(self.number)
        self._signals.finished.emit(self.number, image)


class Cell(QLabel):
    clicked = Signal(int)  # index

    def __init__(self, parent: "AlbumScrollWidgetBasic"):
        super().__init__(parent)

        # Qt about
        self.setScaledContents(True)  # Scale the pixmap to fill the label

        #
        self._index: Optional[int] = None  # The index this unit is currently showing (or assigned)]
        # Callable that generates a QImage given an index
        self._provider: Optional["AssetImageProvider"] = None
        self._pool = QThreadPool.globalInstance()
        self._active_task = None  # 跟踪当前加载任务

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, idx):
        """
        Assign a new index and initiate asynchronous image loading.
        If no image provider is set, this does nothing.

        Args:
            idx: The numeric index to display.
        """
        self._index = idx

        # 取消旧任务
        if self._active_task is not None:
            self._active_task.signals.finished.disconnect(self._on_image_loaded)
            self._active_task = None

        if self._provider and idx is not None:
            # 任务用 lambda 捕获 provider 和 idx，因为 get_thumbnail 是线程安全方法
            task = ImageLoadTask(idx, lambda i: self._provider.get_thumbnail(i))
            task.signals.finished.connect(self._on_image_loaded)
            self._active_task = task
            self._pool.start(task)

    @Slot(object, object)
    def _on_image_loaded(self, number, image: QImage):
        if number == self._index and not image.isNull():
            self.setPixmap(QPixmap.fromImage(image))
        self.setPixmap(QPixmap.fromImage(image))
        # 任务完成后清除引用（此时连接已触发，可以断开）
        self._active_task = None


class AssetImageProvider(QObject):
    """
    为虚拟滚动组件提供缩略图的异步数据源。
    所有会在工作线程调用的方法都设计为线程安全（除 GUI 回调）。
    """

    def __init__(self, album_repo, thumbnail_type: AssetImageType = AssetImageType.THUMB_SMALL):
        super().__init__()
        self._repo = album_repo
        self._thumbnail_type = thumbnail_type  # 决定使用哪个缩略图字段及尺寸
        self._items: List[Dict] = []  # 缓存的全量资产简要信息
        self._mutex = QMutex()
        self._cache: OrderedDict[int, QImage] = OrderedDict()
        self._max_cache = 200  # 最多缓存 200 张缩略图

    # ---------- 数据加载 ----------
    def load_album(self, album_id: int, sort_by: AlbumAssetSortOption = AlbumAssetSortOption.TAKEN_AT):
        """加载指定相簿的全部资产 ID 和路径信息（工作线程或主线程均可，完成后更新列表）"""
        # 这里调用 repo 获取全量（对于超大相簿，repo 可能需要调整，见下文说明）
        assets = self._repo.get_album_assets(album_id, sort_by, limit=0)  # 假设 limit=0 返回全部
        # 如果 repo 不支持全量，可改为循环分页拉取
        new_items = []
        for a in assets:
            new_items.append({
                'id': a['id'],
                'file_path': a['file_path'],
                'thumb_small': a.get('thumb_small_path'),
                'thumb_medium': a.get('thumb_medium_path'),
                'thumb_large': a.get('thumb_path'),
                'mime_type': a['mime_type'],
                'width': a['width'],
                'height': a['height']
            })
        with QMutexLocker(self._mutex):
            self._items = new_items
            self._cache.clear()
        # 通知外界总数变化（主线程通过信号，但可直接由调用方负责刷新 UI）
        # 我们暴露 total_items 属性供虚拟滚动查询

    @property
    def total_items(self) -> int:
        with QMutexLocker(self._mutex):
            return len(self._items)

    # ---------- 缩略图生成（工作线程调用） ----------
    def get_thumbnail(self, index: int) -> QImage:
        """根据全局索引生成/加载缩略图。线程安全。"""
        # 1. 查缓存
        with QMutexLocker(self._mutex):
            if index in self._cache:
                # 移动到最后（LRU）
                img = self._cache.pop(index)
                self._cache[index] = img
                return img

            if index < 0 or index >= len(self._items):
                return self._create_placeholder(index)

            item = self._items[index]

        # 2. 优先使用已存在的缩略图文件
        thumb_path = self._get_thumb_path(item)
        if thumb_path and os.path.isfile(thumb_path):
            img = self._load_image(thumb_path)
            if not img.isNull():
                self._add_to_cache(index, img)
                return img

        # 3. 回退：用原图实时生成缩略图（不阻塞 UI，已在工作线程）
        #    这里可以根据 mime_type 决定是否只处理图片
        if item['file_path'] and os.path.isfile(item['file_path']):
            img = self._generate_thumbnail_from_original(item['file_path'])
            if not img.isNull():
                self._add_to_cache(index, img)
                return img

        # 4. 完全失败：返回占位图
        return self._create_placeholder(index)

    def _get_thumb_path(self, item: Dict) -> Optional[str]:
        """根据当前缩略图类型返回可能存在的文件路径"""
        if self._thumbnail_type == AssetImageType.THUMB_SMALL:
            return item['thumb_small']
        elif self._thumbnail_type == AssetImageType.THUMB_MEDIUM:
            return item['thumb_medium']
        elif self._thumbnail_type == AssetImageType.THUMB_LARGE:
            return item['thumb_large']
        return None

    @staticmethod
    def _load_image(path: str) -> QImage:
        """安全读取图像文件（工作线程可用）"""
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        return reader.read()

    def _generate_thumbnail_from_original(self, original_path: str) -> QImage:
        """使用原图生成指定尺寸的缩略图"""
        max_size = self._thumbnail_type.max_size
        if max_size is None:
            max_size = 256  # 原图类型不应该走这里，但保留 fallback
        reader = QImageReader(original_path)
        reader.setAutoTransform(True)
        # 根据原图尺寸计算等比缩放
        orig_size = reader.size()
        if orig_size.isValid():
            scaled = orig_size.scaled(max_size, max_size, Qt.KeepAspectRatio)
            reader.setScaledSize(scaled)
        return reader.read()

    def _add_to_cache(self, index: int, img: QImage):
        with QMutexLocker(self._mutex):
            self._cache[index] = img
            while len(self._cache) > self._max_cache:
                self._cache.popitem(last=False)  # 删除最久未用

    @staticmethod
    def _create_placeholder(index: int) -> QImage:
        """生成一个显示索引数字的占位图（复用你原来的 image_provider 逻辑）"""
        # 直接调用你已有的 image_provider 函数，或者内联简单绘制
        return image_provider(index)


class AlbumScrollWidgetBasic(QWidget):
    scroll_changed = Signal(int)
    unit_clicked = Signal(int)

    class Pool:
        def __init__(self, max_size=20, factory: Callable = None):
            self._pool: Set[Cell] = set()
            self.max_size = max_size
            self.factory = factory

        @property
        def pool(self) -> Set[Cell]:
            return self._pool

        def acquire(self):
            """从池中取出一个，如果没有就用 factory 创建新的"""
            if self._pool:
                return self._pool.pop()
            if self.factory is None:
                raise RuntimeError("Pool is empty and no factory provided")
            return self.factory() if self.factory else None

        def release(self, obj):
            """将对象放回池中，若超过最大容量则随机销毁"""
            obj: Cell

            # obj.reset()  # 清理对象状态

            # if hasattr(obj, '_active_task') and obj._active_task is not None:
            #     obj._active_task.signals.finished.disconnect(obj._on_image_loaded)
            #     obj._active_task = None
            obj.hide()
            # Clear the pixmap and mark as unused
            # obj.clear()
            obj.setPixmap(QPixmap())  # 清空显示
            obj.index = None
            obj.clicked.disconnect()
            obj._provider = None

            self._pool.add(obj)
            while len(self._pool) > self.max_size:
                old = self._pool.pop()
                old.deleteLater()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Qt about
        # Enable keyboard focus to receive key events for scrolling
        self.setFocusPolicy(Qt.StrongFocus)

        #
        self._pool = self.Pool(
            CACHE_POOL_MAX_ITEM_NUMBER,
            lambda: Cell(self),
        )
        self._provider: Optional[AssetImageProvider] = None

        # temp
        self._scroll_y = 0.0
        # Current vertical offset of the content top relative to viewport top (pixels)

        self._image_cells = []

        # Cached visible row range to quickly determine which rows need Cells
        self._visible_row_start = 0
        self._visible_row_end = 0
        self._max_item_index = MAX_ITEM_INDEX

        # Configurable attr
        # Total virtual height of all content (computed based on row count and cell size)
        self._total_content_height = TOTAL_CONTENT_HEIGHT
        # Scrolling step per wheel delta cell (120 delta = one "notch")
        self._wheel_pixel_step = WHEEL_PIXEL_STEP
        self.overscroll_top = OVERSCROLL_TOP_MAX  # 顶部允许的最大空白像素，设为0则关闭效果
        self.single_row_num = DEFAULT_COLUMN_COUNT  # 每行项目数
        self.fallback_cell_size = FALLBACK_CELL_SIZE

        # alias
        self.layout_ = self._update_visible_cells

    @property
    def provider(self) -> Optional[AssetImageProvider]:
        return self._provider

    @provider.setter
    def provider(self, value: Optional[AssetImageProvider]):
        self._provider = value

    # signal
    def _on_unit_clicked(self, index: int):
        """内部槽：当任意 Unit 被点击时，转发该信号"""
        self.unit_clicked.emit(index)

    # calculate
    def _get_cell_size(self) -> int:
        """
        Calculate the side length of a single grid cell based on the widget's current width
        and the configured number of columns.

        Returns:
            A positive integer representing the cell size in pixels.
        """
        w = self.contentsRect().width()
        if w <= 0:  # if widget has no valid width
            return self.fallback_cell_size  # fallback size
        return w // self.single_row_num

    def _index_to_row_col(self, idx: int):
        """
        Convert a linear item index to its row and column in the grid.

        Args:
            idx: The global item index.

        Returns:
            A tuple (row, col) where both are zero-based.
        """
        row = idx // self.single_row_num
        col = idx % self.single_row_num
        return row, col

    def _row_col_to_index(self, row: int, col: int):
        """
        Convert a (row, col) grid coordinate to a global linear index.

        Args:
            row: Zero-based row number.
            col: Zero-based column number.

        Returns:
            The global item index.
        """
        return row * self.single_row_num + col

    # flush
    def _update_total_height(self):
        total_items = self._max_item_index + 1 if self._max_item_index is not None else 0
        total_rows = (total_items + self.single_row_num - 1) // self.single_row_num
        cell_sz = self._get_cell_size()
        self._total_content_height = total_rows * cell_sz
        self._total_rows = total_rows

    def _update_visible_cells(self):
        """
        Update the set of cell widgets to only show those that are visible in the current viewport.
        Steps:
            1. Determine the range of rows currently intersecting the viewport.
            2. Compute the set of global indices that should be visible.
            3. Detach and hide cells that are no longer needed, moving them to the reuse pool.
            4. Create or recycle cell instances for the new visible indices.
            5. Position and show each visible cell.
        """

        # precheck
        if not self.isVisible():
            return

        cell_sz = self._get_cell_size()
        if cell_sz <= 0:
            return

        #
        rect = self.contentsRect()
        viewport_h = rect.height()

        # 1. Calculate the range of rows that are visible
        first_visible_row = max(0, int(self._scroll_y // cell_sz))
        # Bottom Y coordinate of the content that is visible
        bottom_y = self._scroll_y + viewport_h
        last_visible_row = int((bottom_y + cell_sz - 1) // cell_sz)
        # include the last row partially visible

        # Clamp to the total number of rows (using the fixed huge number)
        total_items = self._max_item_index + 1  # _max_item_index 是最大有效索引
        if total_items <= 0:
            return
        total_rows = (total_items + self.single_row_num - 1) // self.single_row_num

        last_visible_row = min(last_visible_row, total_rows - 1)
        if first_visible_row > last_visible_row:
            return

        # Update cache attr
        self._visible_row_start = first_visible_row
        self._visible_row_end = last_visible_row

        # 2 & 3.
        # Release cells that are no longer visible by comparing the current active
        # cell map against the set of indices required for the current viewport.
        needed_indices = self._get_all_needed_indices(
            first_visible_row, last_visible_row
        )
        self._clear_cells(
            self._build_existing_cell_map(),
            needed_indices
        )

        # 4 & 5. Create/reuse cells and lay them out
        self._update_cells_for_indices(needed_indices, cell_sz)

    def _update_cells_for_indices(self, needed_indices, cell_sz):
        """
        Ensure a Cell is present and correctly positioned for every index in
        needed_indices. Reuses existing active cells when possible, otherwise
        acquires from the pool. Connects signals and shows the cell.

        Args:
            needed_indices: set of global grid indices that must be visible.
            cell_sz: current side length of a single cell in pixels.
        """
        # Rebuild the active cell map (may have changed after recycling)
        current_map = self._build_existing_cell_map()

        for idx in needed_indices:
            if idx in current_map:
                cell = current_map[idx]
            else:
                cell: Cell = self._pool.acquire()
                cell._provider = self._provider
                cell.index = idx  # triggers async loading
                cell.clicked.connect(self._on_unit_clicked, Qt.UniqueConnection)
                self._image_cells.append(cell)

            row, col = self._index_to_row_col(idx)
            x = col * cell_sz
            y = int(row * cell_sz - self._scroll_y)
            cell.setGeometry(x, y, cell_sz, cell_sz)
            cell.show()

    def update_max_item_index(self, index: int):
        self._max_item_index = index

    # tool
    def _get_all_needed_indices(self, first_visible_row, last_visible_row):
        """Gather all global indices that need to be displayed"""
        needed_indices = set()
        for row in range(first_visible_row, last_visible_row + 1):
            for col in range(self.single_row_num):
                idx = self._row_col_to_index(row, col)
                needed_indices.add(idx)
        return needed_indices

    def _build_existing_cell_map(self):
        """Build a mapping of index to existing active cell"""
        cell: Cell
        return {
            cell.index: cell for cell in self._image_cells
            if cell.index is not None
        }

    def _clear_cells(self, existing_map, needed_indices):
        """Remove cells that are no longer needed (move to reuse pool)"""
        for idx, cell in list(existing_map.items()):
            if idx not in needed_indices:
                self._release_cell(cell)

    def _release_cell(self, cell):
        # 从活跃列表移除
        if cell in self._image_cells:
            self._image_cells.remove(cell)
        # 放回复用池
        self._pool.release(cell)


# import traceback
#
#
# def try_exc(func):
#     def wrapper(*args, **kwargs):
#         try:
#             return func(*args, **kwargs)
#         except Exception:  # noqa
#             traceback.print_exc()
#
#     return wrapper
#
#
# class RoundedCell(Cell):
#     """继承原 Cell，在线程中把原图处理成圆角图后再显示。"""
#
#     def __init__(self, parent: "AlbumScrollWidgetBasic"):
#         super().__init__(parent)
#         # 关闭 QLabel 的缩放，因为我们已经给了精确尺寸的 pixmap
#         self.setScaledContents(False)
#
#     @Cell.index.setter
#     def index(self, idx):
#         self._index = idx
#         if self._provider is None or idx is None:
#             return
#
#         # 从父控件获取当前 cell 尺寸和圆角半径（在主线程中安全）
#         widget = self.parent()
#         if not isinstance(widget, AlbumScrollWidgetRounded):
#             # 理论上不会发生
#             return
#
#         cell_sz = widget._get_cell_size()  # noqa
#         radius = widget.corner_radius
#
#         # 将圆角处理直接放到 ImageLoadTask 的 lambda 里，
#         # 这样缩放+裁剪+圆角都在后台线程完成
#         task = ImageLoadTask(
#             idx,
#             lambda i, sz=cell_sz, r=radius, prov=self._provider: make_rounded_image(
#                 prov.get_thumbnail(i), QSize(sz, sz), r
#             ),
#         )
#         task.signals.finished.connect(self._on_image_loaded)
#         self._pool.start(task)
#
#
# class AlbumScrollWidgetRounded(AlbumScrollWidgetBasic):
#     """带圆角缩略图的 Album 滚动控件。"""
#
#     def __init__(self, parent=None):
#         super().__init__(parent)
#
#         # 圆角半径（单位：像素）
#         self._corner_radius = 8
#
#         # 将对象池的工厂函数替换为 RoundedCell
#         # 注意：这里会清空池中已有的 Cell（如果有）
#         self._pool = self.Pool(
#             CACHE_POOL_MAX_ITEM_NUMBER,
#             lambda: RoundedCell(self),
#         )
#
#     # ---------- 圆角属性 ----------
#     @property
#     def corner_radius(self) -> int:
#         return self._corner_radius
#
#     @corner_radius.setter
#     def corner_radius(self, r: int):
#         if r != self._corner_radius:
#             self._corner_radius = r
#             # 让所有可见 Cell 重新加载（会使用新的半径）
#             self._reload_visible_cells()
#
#     # ---------- 尺寸变化时重新生成圆角图 ----------
#     @try_exc
#     def resizeEvent(self, event):
#         old_size = self._get_cell_size()
#         super().resizeEvent(event)
#         new_size = self._get_cell_size()
#         if new_size != old_size:
#             # cell 尺寸变了，所有已显示的图片需要以新尺寸重绘
#             self._reload_visible_cells()
#
#     @try_exc
#     def _reload_visible_cells(self):
#         """强制所有当前显示的 Cell 重新加载图片（使用新的 cell size 和圆角半径）。"""
#         for cell in self._image_cells:
#             if cell.index is not None:
#                 # 重新触发加载（会在线程中按当前 cell_size 和 radius 生成新图）
#                 idx = cell.index
#                 cell.index = idx   # setter 会启动新任务


# class AlbumScrollWidget(AlbumScrollWidgetRounded):
class AlbumScrollWidget(AlbumScrollWidgetBasic):

    def __init__(self, parent=None):
        super().__init__(parent)

        # cache
        self._cached_anchor_index: Optional[int] = None

        # Wheel conf
        self._wheel_inverted = WHEEL_INVERTED
        self._wheel_pixel_step = WHEEL_PIXEL_STEP

    # ==================== 可配置项 ====================
    def set_wheel_inverted(self, inverted: bool):
        self._wheel_inverted = inverted

    def is_wheel_inverted(self) -> bool:
        return self._wheel_inverted

    def set_wheel_pixel_step(self, step: int):
        self._wheel_pixel_step = step

    # ==================== 滚动控制接口 ====================
    def scroll_by(self, delta_y: float):
        """按像素滚动，正值向下，负值向上。"""
        old_y = self._scroll_y
        new_y = int(old_y + delta_y)

        # 限制滚动范围
        max_scroll = max(0, self._total_content_height - self.contentsRect().height())
        min_scroll = -self.overscroll_top
        new_y = max(min_scroll, min(max_scroll, new_y))

        if abs(new_y - old_y) < 0.5:
            return

        self._scroll_y = new_y
        self._after_scroll(new_y)

    def scroll_up(self, pixels: float = None):
        if pixels is None:
            pixels = self.contentsRect().height() / SCROLL_LINE_FRACTION
        self.scroll_by(-pixels)

    def scroll_down(self, pixels: float = None):
        if pixels is None:
            pixels = self.contentsRect().height() / SCROLL_LINE_FRACTION
        self.scroll_by(pixels)

    def scroll_to_top(self):
        self._scroll_y = 0.0
        self._after_scroll()

    def scroll_to_bottom(self):
        max_scroll = max(0, self._total_content_height - self.contentsRect().height())
        self._scroll_y = max_scroll
        self._after_scroll()

    def set_scroll_y(self, y: float):
        max_scroll = max(0, self._total_content_height - self.contentsRect().height())
        min_scroll = -self.overscroll_top
        self._scroll_y = max(min_scroll, min(max_scroll, int(y)))
        self._after_scroll()

    def get_scroll_y(self) -> float:
        return self._scroll_y

    # ==================== 动态列数切换 ====================
    def _after_scroll(self, new_y=None):
        """每次滚动后的统一收尾：刷新视图 + 缓存新锚点"""
        self._update_visible_cells()
        if new_y is not None:
            self.scroll_changed.emit(new_y)
        else:
            self.scroll_changed.emit(self._scroll_y)
        # 缓存新的锚点索引
        self._cached_anchor_index = self._compute_viewport_center_index()

    def _compute_viewport_center_index(self) -> Optional[int]:
        """
        基于当前的 _scroll_y、视口尺寸、cell 大小，
        返回视口正中央对应的全局项目索引。
        """
        cell_sz = self._get_cell_size()
        if cell_sz <= 0:
            return None

        viewport_h = self.contentsRect().height()
        # 内容坐标中心
        content_center_y = self._scroll_y + viewport_h / 2

        # 对应的行和列（这里取该行的中间列）
        row = int(content_center_y // cell_sz)
        col = self.single_row_num // 2  # 大致中间列

        index = row * self.single_row_num + col
        # 限制在有效范围
        if self._max_item_index is not None:
            index = max(0, min(self._max_item_index, index))
        return index

    def change_single_row_num(self, new_cols: int):
        if new_cols == self.single_row_num:
            return

        anchor = self._cached_anchor_index
        self.single_row_num = new_cols
        self._update_total_height()

        if anchor is not None:
            new_cell_sz = self._get_cell_size()
            new_row = anchor // self.single_row_num
            target_y = new_row * new_cell_sz + new_cell_sz / 2
            new_scroll_y = int(target_y - self.contentsRect().height() / 2)
        else:
            new_scroll_y = self._scroll_y

        max_scroll = max(0, self._total_content_height - self.contentsRect().height())
        self._scroll_y = max(0.0, min(max_scroll, new_scroll_y))
        self._after_scroll()  # 这里已经包含 _update_visible_cells 和 signal

    # ==================== 窗口大小变化 ====================
    def resizeEvent(self, event):
        # 暂时不要做任何与 size 有关的计算！
        anchor = self._cached_anchor_index

        super().resizeEvent(event)
        self._update_total_height()

        if anchor is not None:
            new_cell_sz = self._get_cell_size()
            new_row = anchor // self.single_row_num
            # 让锚点项的中心落在视口中心
            target_y = new_row * new_cell_sz + new_cell_sz / 2
            new_scroll_y = int(target_y - self.contentsRect().height() / 2)
        else:
            new_scroll_y = self._scroll_y

        max_scroll = max(0, self._total_content_height - self.contentsRect().height())
        self._scroll_y = max(0.0, min(max_scroll, new_scroll_y))
        self._update_visible_cells()
        self.scroll_changed.emit(self._scroll_y)

    # ==================== 键鼠事件 ====================
    def wheelEvent(self, event):
        # 检测 Ctrl 修饰键
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            # 可根据需要适配反转
            if not self._wheel_inverted:
                delta = -delta

            # 向上滚（放大）→ 减少列数，向下滚（缩小）→ 增加列数
            if delta > 0:
                new_cols = self.single_row_num - 1
            elif delta < 0:
                new_cols = self.single_row_num + 1
            else:
                return

            # 限制合理范围（例如 1 ~ 20）
            new_cols = max(1, min(20, new_cols))
            if new_cols != self.single_row_num:
                self.change_single_row_num(new_cols)

            event.accept()
            return

        delta = event.angleDelta().y()
        if self._wheel_inverted:
            delta = -delta
        step = self._wheel_pixel_step * (delta / WHEEL_DELTA_BASE)
        self.scroll_by(step)
        event.accept()

    def keyPressEvent(self, event):
        cell_sz = self._get_cell_size()
        match event.key():
            case Qt.Key.Key_Up:
                self.scroll_by(-cell_sz)
            case Qt.Key_Down:
                self.scroll_by(cell_sz)
            case Qt.Key_PageUp:
                self.scroll_by(-self.contentsRect().height() + cell_sz)
            case Qt.Key_PageDown:
                self.scroll_by(self.contentsRect().height() - cell_sz)
            case Qt.Key_Home:
                self.scroll_to_top()
            case Qt.Key_End:
                self.scroll_to_bottom()
            case _:
                super().keyPressEvent(event)


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout

    app = QApplication(sys.argv)


    # def notify(a0, a1):
    #     print(a0, a1)
    #     return QApplication.notify(app, a0, a1)
    #
    #
    # app.notify = notify

    # Quick test: create a virtual scrolling widget with inverted wheel direction.
    w1 = AlbumScrollWidget()
    # w1.set_wheel_inverted(True)
    w1.show()

    debug_window = QWidget()
    layout = QVBoxLayout(debug_window)
    layout_btn: QPushButton = QPushButton("Layout")
    layout_btn.clicked.connect(w1.layout_)
    layout.addWidget(layout_btn)
    debug_window.setLayout(layout)

    debug_window.show()

    provider = AssetImageProvider(None)
    w1.provider = provider
    # w1._max_item_index = 100
    w1.corner_radius = 8

    exit(app.exec())
