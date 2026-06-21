#
""""""

from typing import Dict, Optional

from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget

# 以下常量假设与原项目定义一致，可根据实际需要修改
DEFAULT_COLUMN_COUNT = 5           # 每行显示数量
FALLBACK_CELL_SIZE = 100           # 无有效宽度时的默认单元格大小
WHEEL_PIXEL_STEP = 30              # 滚轮滚动步长（像素）
OVERSCROLL_TOP_MAX = 100           # 顶部允许的最大过滚距离
MAX_ITEM_INDEX = 10000             # 默认最大索引（用于计算总高度）
CACHE_POOL_MAX_ITEM_NUMBER = 200   # 最大缓存 QPixmap 数量


class VirtualScrollGrid(QWidget):
    """基于直接绘制的虚拟滚动网格组件。

    信号：
        scroll_changed(int): 当滚动偏移量发生变化时发射，参数为当前的 scroll_y。
        unit_clicked(int):   当用户点击某个网格项时发射，参数为该项的全局索引。
    """
    scroll_changed = Signal(int)
    unit_clicked = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)      # 允许接收键盘事件（用于方向键滚动等）

        # ---------- 配置参数 ----------
        self.single_row_num = DEFAULT_COLUMN_COUNT      # 每行列数
        self.fallback_cell_size = FALLBACK_CELL_SIZE    # 无有效宽度时的默认单元格大小
        self._wheel_pixel_step = WHEEL_PIXEL_STEP       # 滚轮一次滚动的像素数
        self.overscroll_top = OVERSCROLL_TOP_MAX        # 顶部过滚距离（0 则无弹性效果）

        # ---------- 内部状态 ----------
        self._scroll_y = 0.0                # 当前内容顶边相对于视口顶边的偏移（像素）
        self._max_item_index = MAX_ITEM_INDEX  # 最大有效项目索引
        self._total_content_height = 0      # 虚拟内容总高度
        self._total_rows = 0                # 总行数

        # ---------- 图像缓存 ----------
        self._pixmap_cache: Dict[int, QPixmap] = {}   # 索引 -> QPixmap
        self._max_cache_size = CACHE_POOL_MAX_ITEM_NUMBER

        # 初始化总高度
        self._update_total_height()

    # ==================== 公共接口 ====================

    def set_pixmap(self, index: int, pixmap: QPixmap) -> None:
        """设置指定索引处的图像。

        如果缓存已满，会移除最早添加的一个条目（FIFO）。调用后会自动触发重绘。

        Args:
            index:  网格项全局索引（从 0 开始）。
            pixmap: 要显示的 QPixmap。
        """
        if index < 0:
            return

        # 如果缓存已满，移除最早的一个 key（保持字典插入顺序）
        if len(self._pixmap_cache) >= self._max_cache_size and index not in self._pixmap_cache:
            first_key = next(iter(self._pixmap_cache))
            del self._pixmap_cache[first_key]

        self._pixmap_cache[index] = pixmap
        self.update()

    def update_max_item_index(self, index: int) -> None:
        """更新最大有效索引，并重新计算总内容高度。

        Args:
            index: 新的最大项目索引。
        """
        self._max_item_index = index
        self._update_total_height()
        self.update()

    def clear_cache(self) -> None:
        """清空所有缓存的 QPixmap 并触发重绘。"""
        self._pixmap_cache.clear()
        self.update()

    def set_scroll_y(self, y: float) -> None:
        """设置当前滚动偏移（像素），触发重绘并发射 scroll_changed 信号。"""
        # 允许顶部过滚，底部硬边界（与原始逻辑一致）
        max_scroll = self._total_content_height - self.contentsRect().height()
        if max_scroll < 0:
            max_scroll = 0
        clamped = max(-self.overscroll_top, int(min(y, max_scroll)))
        if clamped != self._scroll_y:
            self._scroll_y = clamped
            self.scroll_changed.emit(int(self._scroll_y))
            self.update()

    # ==================== 尺寸计算 ====================

    def _get_cell_size(self) -> int:
        """根据当前部件宽度和列数计算单元格边长。"""
        w = self.contentsRect().width()
        if w <= 0:
            return self.fallback_cell_size
        return w // self.single_row_num

    def _index_to_row_col(self, idx: int) -> tuple[int, int]:
        """线性索引转为 (行, 列)。"""
        row = idx // self.single_row_num
        col = idx % self.single_row_num
        return row, col

    def _row_col_to_index(self, row: int, col: int) -> int:
        """(行, 列) 转为线性索引。"""
        return row * self.single_row_num + col

    def _update_total_height(self) -> None:
        """根据最大索引和单元格尺寸更新虚拟内容总高度。"""
        total_items = self._max_item_index + 1 if self._max_item_index is not None else 0
        total_rows = (total_items + self.single_row_num - 1) // self.single_row_num
        cell_sz = self._get_cell_size()
        self._total_content_height = total_rows * cell_sz
        self._total_rows = total_rows

    # ==================== 绘制 ====================

    def paintEvent(self, event) -> None:
        """绘制当前视口内可见的图像。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        cell_sz = self._get_cell_size()
        if cell_sz <= 0:
            return

        rect = self.contentsRect()
        viewport_h = rect.height()

        # 1. 计算可见行范围
        first_row = max(0, int(self._scroll_y // cell_sz))
        bottom_y = self._scroll_y + viewport_h
        last_row = int((bottom_y + cell_sz - 1) // cell_sz)
        last_row = min(last_row, self._total_rows - 1)

        if first_row > last_row:
            return

        # 2. 遍历可见单元格并绘制
        for row in range(first_row, last_row + 1):
            for col in range(self.single_row_num):
                idx = self._row_col_to_index(row, col)
                if idx in self._pixmap_cache:
                    pixmap = self._pixmap_cache[idx]
                    # 计算绘制矩形（相对于视口）
                    x = col * cell_sz
                    y = int(row * cell_sz - self._scroll_y)
                    target_rect = QRect(x, y, cell_sz, cell_sz)
                    # 缩放到单元格大小并绘制
                    painter.drawPixmap(target_rect, pixmap)
                # 可选：为没有图像的位置绘制占位符
                # else:
                #     painter.setPen(QPen(QColor(200,200,200)))
                #     painter.drawRect(x, y, cell_sz-1, cell_sz-1)

    # ==================== 事件处理 ====================

    def wheelEvent(self, event) -> None:
        """鼠标滚轮滚动事件。"""
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return

        # 计算滚动步长（考虑系统设置）
        step = self._wheel_pixel_step
        # 反转方向：向下滚增加 scroll_y
        new_y = self._scroll_y - delta / 120.0 * step

        # 限制滚动范围（带 overscroll_top）
        max_scroll = self._total_content_height - self.contentsRect().height()
        if max_scroll < 0:
            max_scroll = 0

        # 允许顶部过滚
        if new_y < -self.overscroll_top:
            new_y = -self.overscroll_top
        # 底部不能过滚
        if new_y > max_scroll:
            new_y = max_scroll

        if new_y != self._scroll_y:
            self._scroll_y = new_y
            self.scroll_changed.emit(int(self._scroll_y))
            self.update()

        event.accept()

    def mousePressEvent(self, event) -> None:
        """鼠标点击事件，用于识别点击了哪个网格项。"""
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            cell_sz = self._get_cell_size()
            if cell_sz <= 0:
                return

            # 计算点击位置对应的行列
            col = pos.x() // cell_sz
            row = int((pos.y() + self._scroll_y) // cell_sz)

            if col >= self.single_row_num or row >= self._total_rows:
                return

            idx = self._row_col_to_index(row, col)
            # 只对已缓存图像的区域发射信号（可改为总是发射）
            if idx in self._pixmap_cache:
                self.unit_clicked.emit(idx)

        super().mousePressEvent(event)

    def resizeEvent(self, event) -> None:
        """部件尺寸改变时重新计算总高度并重绘。"""
        self._update_total_height()
        super().resizeEvent(event)
        self.update()

    def keyPressEvent(self, event) -> None:
        """支持方向键滚动。"""
        step = self._wheel_pixel_step
        if event.key() == Qt.Key_Down:
            self._scroll_y += step
        elif event.key() == Qt.Key_Up:
            self._scroll_y -= step
        elif event.key() == Qt.Key_PageDown:
            self._scroll_y += self.contentsRect().height()
        elif event.key() == Qt.Key_PageUp:
            self._scroll_y -= self.contentsRect().height()
        else:
            super().keyPressEvent(event)
            return

        # 限制滚动范围（同滚轮逻辑）
        max_scroll = self._total_content_height - self.contentsRect().height()
        if max_scroll < 0:
            max_scroll = 0
        self._scroll_y = max(-self.overscroll_top, int(min(self._scroll_y, max_scroll)))
        self.scroll_changed.emit(int(self._scroll_y))
        self.update()

if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QImage, QFont, QColor

    app = QApplication(sys.argv)


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

    grid = VirtualScrollGrid()
    grid.set_pixmap(0, QPixmap(image_provider(0)))
    grid.set_pixmap(1, QPixmap(image_provider(1)))
    grid.set_scroll_y(110)  # 滚动到 y=150 像素处

    grid.show()

    app.exec()
