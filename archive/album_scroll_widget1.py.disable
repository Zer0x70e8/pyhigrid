# album_scroll_widget.py
"""
Virtual scrolling widget for displaying a grid of images (or placeholders) asynchronously.

This module provides a `VirtualScrolledWidget` that supports smooth pixel-level scrolling over
a virtually infinite list of items, rendered in a grid layout. Each item is represented by a `Unit`
(QLabel) that loads its content asynchronously via a thread pool and a user-provided image provider
function. The widget reuses `Unit` objects to minimise memory usage and only manages those currently
visible in the viewport.
"""

from typing import List

from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor, QImage
from PySide6.QtCore import QThreadPool, QRunnable, Signal, QObject, Slot, Qt


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


class _ImageLoadTaskSignals(QObject):
    """Signals for the image loading task."""
    finished = Signal(object, object)  # number, QImage


class _ImageLoadTask(QRunnable):
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
        self._signals = _ImageLoadTaskSignals()

    @property
    def signals(self):
        return self._signals

    def run(self):
        """Execute the image generation and emit the result via signal."""
        # func returns QImage (safe for cross-thread signals)
        image = self.func(self.number)
        self._signals.finished.emit(self.number, image)


class Unit(QLabel):
    """
    A single display cell that asynchronously loads and displays an image.
    Each Unit holds a reference to an image provider function and its current index.
    When the index is set, a thread-pool task is started to generate the image,
    and the result is applied on the main thread.
    """

    clicked = Signal(int)  # index

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image_provider = None  # Callable that generates a QImage given an index
        self.current_number = None  # The index this unit is currently showing (or assigned)
        self._pool = QThreadPool.globalInstance()
        self.setScaledContents(True)  # Scale the pixmap to fill the label

    def set_index(self, index):
        """
        Assign a new index and initiate asynchronous image loading.
        If no image provider is set, this does nothing.

        Args:
            index: The numeric index to display.
        """
        if self._image_provider is None:
            return
        self.current_number = index
        task = _ImageLoadTask(index, self._image_provider)
        task.signals.finished.connect(self._on_image_loaded)
        self._pool.start(task)

    @Slot(object, object)
    def _on_image_loaded(self, number, image: QImage):
        """
        Slot called when the image generation task finishes.
        Only applies the image if the unit still corresponds to the same index,
        preventing out-of-date results from updating the widget.

        Args:
            number: The index the image was generated for.
            image: The generated QImage.
        """
        if number != self.current_number:
            return
        # Convert QImage to QPixmap on the main thread (safe).
        pixmap = QPixmap.fromImage(image)
        self.setPixmap(pixmap)

    def mousePressEvent(self, event):
        if self.current_number is not None:
            self.clicked.emit(self.current_number)
        super().mousePressEvent(event)

class VirtualScrolledWidget(QWidget):
    """
    A virtual scrolling widget that arranges an infinitely large grid of items
    (displayed as Unit objects) and supports pixel-level smooth scrolling.

    Characteristics:
    - Only a small number of Unit widgets are created and recycled, keeping memory usage low.
    - Images are loaded asynchronously via a thread pool.
    - Scrolling can be performed with the mouse wheel, keyboard, or programmatically.
    - The number of columns can be changed dynamically, and the scroll position adjusts to keep
      the same visual region stable.
    """

    scroll_changed = Signal(int)
    unit_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._single_row_num = 5  # Number of columns (items per row)
        self._max_cached_units = 20  # Maximum number of recycled Unit objects to keep

        self._scroll_y = 0.0
        # Current vertical offset of the content top relative to viewport top (pixels)
        self._total_content_height = 0
        # Total virtual height of all content (computed based on row count and cell size)

        self._image_units: List[Unit] = []  # Currently visible/active Unit instances
        self._image_units_reuse_pool: List[Unit] = []  # Pool of detached Unit instances for reuse

        # Cached visible row range to quickly determine which rows need Units
        self._visible_row_start = 0
        self._visible_row_end = 0

        # Enable keyboard focus to receive key events for scrolling
        self.setFocusPolicy(Qt.StrongFocus)

        # Scrolling step per wheel delta unit (120 delta = one "notch")
        self._wheel_pixel_step = 30
        self.overscroll_top = 0   # 顶部允许的最大空白像素，设为0则关闭效果

        # Flag to invert the mouse wheel direction
        self._wheel_inverted = False

        # alias
        self.layout_ = self._update_visible_units

    def _on_unit_clicked(self, index: int):
        """内部槽：当任意 Unit 被点击时，转发该信号"""
        self.unit_clicked.emit(index)

    def _get_unit_size(self) -> int:
        """
        Calculate the side length of a single grid cell based on the widget's current width
        and the configured number of columns.

        Returns:
            A positive integer representing the cell size in pixels.
        """
        w = self.contentsRect().width()
        if w <= 0:
            return 100  # fallback size when widget has no valid width
        return w // self._single_row_num

    def _update_total_height(self):
        """
        Recompute the total virtual content height based on the assumed number of data rows
        and the current cell size. In a real application, this should use the actual total
        number of rows/lines of data. Here, for demonstration, a very large row count is fixed
        to simulate an infinite list.
        """
        # For demonstration we assume a huge number of rows (1,000,000).
        # In practice, replace this with the actual data row count.
        total_rows = 1000000
        unit_sz = self._get_unit_size()
        self._total_content_height = total_rows * unit_sz

    def _index_to_row_col(self, idx: int):
        """
        Convert a linear item index to its row and column in the grid.

        Args:
            idx: The global item index.

        Returns:
            A tuple (row, col) where both are zero-based.
        """
        row = idx // self._single_row_num
        col = idx % self._single_row_num
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
        return row * self._single_row_num + col

    def _update_visible_units(self):
        """
        Update the set of Unit widgets to only show those that are visible in the current viewport.
        Steps:
            1. Determine the range of rows currently intersecting the viewport.
            2. Compute the set of global indices that should be visible.
            3. Detach and hide units that are no longer needed, moving them to the reuse pool.
            4. Create or recycle Unit instances for the new visible indices.
            5. Position and show each visible unit.
        """
        if not self.isVisible():
            return

        unit_sz = self._get_unit_size()
        if unit_sz <= 0:
            return

        rect = self.contentsRect()
        viewport_h = rect.height()

        # 1. Calculate the range of rows that are visible
        first_visible_row = max(0, int(self._scroll_y // unit_sz))
        # Bottom Y coordinate of the content that is visible
        bottom_y = self._scroll_y + viewport_h
        last_visible_row = int((bottom_y + unit_sz - 1) // unit_sz)
        # include the last row partially visible

        # Clamp to the total number of rows (using the fixed huge number)
        total_rows = 1000000 if self._total_content_height > 0 else 0
        last_visible_row = min(last_visible_row, total_rows - 1)
        if first_visible_row > last_visible_row:
            return

        self._visible_row_start = first_visible_row
        self._visible_row_end = last_visible_row

        # 2. Gather all global indices that need to be displayed
        needed_indices = set()
        for row in range(first_visible_row, last_visible_row + 1):
            for col in range(self._single_row_num):
                idx = self._row_col_to_index(row, col)
                needed_indices.add(idx)

        # 3. Build a mapping of index to existing active Unit
        existing_map = {unit.current_number: unit for unit in self._image_units
                        if unit.current_number is not None}

        # 4. Remove units that are no longer needed (move to reuse pool)
        for idx, unit in list(existing_map.items()):
            if idx not in needed_indices:
                # Remove from active list
                if unit in self._image_units:
                    self._image_units.remove(unit)
                unit.hide()
                # Clear the pixmap and mark as unused
                unit.clear()
                unit.current_number = None
                # Add to reuse pool
                self._image_units_reuse_pool.append(unit)

        # Trim reuse pool to the maximum allowed size
        while len(self._image_units_reuse_pool) > self._max_cached_units:
            old = self._image_units_reuse_pool.pop(0)
            old.deleteLater()

        # 5. Add or reuse units for the newly needed indices
        # Rebuild existing map because it may have changed
        existing_map = {unit.current_number: unit for unit in self._image_units
                        if unit.current_number is not None}

        for idx in needed_indices:
            if idx in existing_map:
                unit = existing_map[idx]
            else:
                # Create a new unit or take one from the reuse pool
                if self._image_units_reuse_pool:
                    unit = self._image_units_reuse_pool.pop()
                else:
                    unit = Unit(self)
                unit._image_provider = image_provider  # Set the image generation function
                unit.current_number = idx
                unit.set_index(idx)  # Initiate async loading
                unit.clicked.connect(self._on_unit_clicked, Qt.UniqueConnection)
                # 使用 UniqueConnection 防止同一个 Unit 被多次连接
                self._image_units.append(unit)

            # Calculate the position of this unit in the viewport
            row, col = self._index_to_row_col(idx)
            x = col * unit_sz
            y = int(row * unit_sz - self._scroll_y)
            unit.setGeometry(x, y, unit_sz, unit_sz)
            unit.show()

    def scroll_by(self, delta_y: float):
        """
        Adjust the vertical scroll position by a given pixel offset.

        Args:
            delta_y: Positive value scrolls down, negative scrolls up.
        """
        old_y = self._scroll_y
        new_y = int(old_y + delta_y)

        # Clamp within valid scroll range
        max_scroll = max(0, self._total_content_height - self.contentsRect().height())
        min_scroll = -self.overscroll_top  # 允许的负向偏移

        new_y = max(min_scroll, min(max_scroll, new_y))

        if abs(new_y - old_y) < 0.5:
            return

        self._scroll_y = new_y
        self._update_visible_units()

        # Emit scroll signal for external synchronisation (e.g., a scrollbar)
        self.scroll_changed.emit(new_y)

    def scroll_up(self, pixels: float = None):
        """
        Scroll upward by a given number of pixels. If no value is provided,
        scrolls by approximately one-tenth of the viewport height.

        Args:
            pixels: Pixels to scroll up (positive). Defaults to viewport height / 10.
        """
        if pixels is None:
            pixels = self.contentsRect().height() / 10
        self.scroll_by(-pixels)

    def scroll_down(self, pixels: float = None):
        """
        Scroll downward by a given number of pixels. If no value is provided,
        scrolls by approximately one-tenth of the viewport height.

        Args:
            pixels: Pixels to scroll down (positive). Defaults to viewport height / 10.
        """
        if pixels is None:
            pixels = self.contentsRect().height() / 10
        self.scroll_by(pixels)

    def set_wheel_inverted(self, inverted: bool):
        """Set whether the mouse wheel direction is inverted."""
        self._wheel_inverted = inverted

    def is_wheel_inverted(self) -> bool:
        """Return whether the mouse wheel direction is currently inverted."""
        return self._wheel_inverted

    def wheelEvent(self, event):
        """Handle mouse wheel events by scrolling the view."""
        delta = event.angleDelta().y()
        if self._wheel_inverted:
            delta = -delta
        # Convert delta to pixel scroll amount using the configured step
        step = self._wheel_pixel_step * (delta / 120)
        self.scroll_by(step)
        event.accept()

    def keyPressEvent(self, event):
        """Handle keyboard events for scrolling (arrows, PageUp/Down, Home/End)."""
        key = event.key()
        unit_sz = self._get_unit_size()
        if key == Qt.Key_Up:
            self.scroll_by(-unit_sz)
        elif key == Qt.Key_Down:
            self.scroll_by(unit_sz)
        elif key == Qt.Key_PageUp:
            page_h = self.contentsRect().height()
            self.scroll_by(-page_h + unit_sz)
        elif key == Qt.Key_PageDown:
            page_h = self.contentsRect().height()
            self.scroll_by(page_h - unit_sz)
        elif key == Qt.Key_Home:
            self.scroll_to_top()
        elif key == Qt.Key_End:
            self.scroll_to_bottom()
        else:
            super().keyPressEvent(event)

    def scroll_to_top(self):
        """Scroll to the top of the content."""
        self._scroll_y = 0.0
        self._update_visible_units()

    def scroll_to_bottom(self):
        """Scroll to the bottom of the content."""
        max_scroll = max(0, self._total_content_height - self.contentsRect().height())
        self._scroll_y = max_scroll
        self._update_visible_units()

    def resizeEvent(self, event):
        """Handle resize events: recompute content height and update visible units."""
        super().resizeEvent(event)
        # Recalculate total height because the cell size may have changed
        self._update_total_height()
        # Ensure the current scroll position does not exceed the new maximum
        max_scroll = max(0, self._total_content_height - self.contentsRect().height())
        min_scroll = -self.overscroll_top
        if self._scroll_y > max_scroll:
            self._scroll_y = max_scroll
        elif self._scroll_y < min_scroll:
            self._scroll_y = min_scroll
        self._update_visible_units()

    def change_single_row_num(self, new_cols: int):
        """
        Dynamically change the number of columns (items per row) while trying to
        maintain the same visual content area centred in the viewport.

        Args:
            new_cols: The new number of columns. If it is the same as the current
                      value, nothing happens.
        """
        if new_cols == self._single_row_num:
            return

        # Identify a central index from the currently visible units
        if self._image_units:
            visible_indices = [u.current_number for u in self._image_units
                               if u.current_number is not None]
            if visible_indices:
                center_idx = sum(visible_indices) // len(visible_indices)
                # Compute the Y coordinate of the centre of this index in the old layout
                old_unit_sz = self._get_unit_size()
                row_old = center_idx // self._single_row_num
                center_y_content = row_old * old_unit_sz + old_unit_sz / 2
                # Offset between viewport centre and content centre
                viewport_center_y = self._scroll_y + self.contentsRect().height() / 2
                offset_to_center = center_y_content - viewport_center_y
            else:
                offset_to_center = 0
                center_idx = 0
        else:
            offset_to_center = 0
            center_idx = 0

        # Apply the new column count
        self._single_row_num = new_cols
        self._update_total_height()

        # Calculate the new Y coordinate of the same index in the new layout
        new_unit_sz = self._get_unit_size()
        new_row = center_idx // self._single_row_num
        new_center_y = new_row * new_unit_sz + new_unit_sz / 2

        # Re-calculate scroll position so that the offset to the centre remains similar
        new_scroll_y = int(new_center_y - offset_to_center - self.contentsRect().height() / 2)
        new_scroll_y = max(0.0, min(
            self._total_content_height - self.contentsRect().height(), new_scroll_y))
        self._scroll_y = new_scroll_y

        self._update_visible_units()

    def get_scroll_y(self) -> float:
        """Return the current vertical scroll offset in pixels."""
        return self._scroll_y

    def set_scroll_y(self, y: float):
        """
        Set the vertical scroll offset to a specific value (clamped to valid range).
        """
        self._scroll_y = max(0.0, min
        (self._total_content_height - self.contentsRect().height(), int(y)))
        self._update_visible_units()


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Quick test: create a virtual scrolling widget with inverted wheel direction.
    w1 = VirtualScrolledWidget()
    w1.set_wheel_inverted(True)
    w1.show()
    exit(app.exec())
