#
""""""

from typing import Optional

from PySide6.QtCore import Qt

from .defs import *
from .widget_basic import VirtualScrollWidgetBasic


class VirtualScrollWidget(VirtualScrollWidgetBasic):

    def __init__(self, parent=None):
        super().__init__(parent)

        # cache
        self._cached_anchor_index: Optional[int] = None

        # Wheel conf
        self._wheel_inverted = WHEEL_INVERTED
        self._zoom_wheel_inverted = WHEEL_INVERTED
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
            if self._zoom_wheel_inverted:
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
        if not self._wheel_inverted:
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
