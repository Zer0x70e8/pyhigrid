#
""""""

from typing import Optional, Callable, Set

from PySide6.QtCore import Qt, Signal
# from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget

from .defs import *
from .cell import Cell
from pyhigrid.ui.gui.server.thumbnail.provider import AssetImageProvider


class VirtualScrollWidgetBasic(QWidget):
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
            obj.clear()
            # obj.setPixmap(QPixmap())  # 清空显示
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
