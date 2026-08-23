#
""""""

from PySide6.QtGui import QPainter, QRegion, QWheelEvent
from PySide6.QtWidgets import QAbstractItemView, QStyleOptionViewItem, QStyle
from PySide6.QtCore import (
    Qt, QRect, QPoint, QModelIndex,
    QItemSelectionModel, QItemSelection
)


class ColumnLayoutCalculator:
    """多列网格布局计算器，仅负责计算每个索引对应的矩形和总高度。"""

    def __init__(self, column_count=1, item_height=160, spacing=5, margin=10):
        self.column_count = max(1, column_count)
        self.item_height = item_height
        self.spacing = spacing
        self.margin = margin

    def compute_rects(self, model, viewport_rect, scroll_offset):
        """返回 {QModelIndex: QRect} 字典，使用均匀列宽避免空隙。"""
        rects = {}
        if not model or model.rowCount() == 0:
            return rects

        available_width = viewport_rect.width() - 2 * self.margin - (self.column_count - 1) * self.spacing
        if available_width <= 0:
            return rects

        base_width = available_width // self.column_count
        remainder = available_width % self.column_count

        col_x = []
        col_w = []
        x = self.margin
        for col in range(self.column_count):
            w = base_width + (1 if col < remainder else 0)
            col_x.append(x)
            col_w.append(w)
            x += w + self.spacing

        for row in range(model.rowCount()):
            grid_row = row // self.column_count
            grid_col = row % self.column_count
            item_rect = QRect(
                col_x[grid_col],
                self.margin + grid_row * (self.item_height + self.spacing) - scroll_offset,
                col_w[grid_col],
                self.item_height
            )
            rects[model.index(row, 0)] = item_rect
        return rects

    def total_height(self, model):
        """计算内容总高度。"""
        if not model or model.rowCount() == 0:
            return 0
        rows_needed = (model.rowCount() + self.column_count - 1) // self.column_count
        return (self.margin * 2 +
                rows_needed * self.item_height +
                (rows_needed - 1) * self.spacing)


class ColumnListView(QAbstractItemView):
    """解耦的多列卡片视图，支持滚轮反转和精确点击。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_mouse_pos = None
        self._column_count = 1
        self._scroll_offset = 0
        self._wheel_inverted = True  # 默认开启滚轮反转
        self._layout_calc = ColumnLayoutCalculator(self._column_count, item_height=160)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setObjectName(type(self).__name__)

    # ========== 滚轮事件 ==========
    def wheelEvent(self, event: QWheelEvent):
        if not self.model():
            return
        delta = event.angleDelta().y()
        if self._wheel_inverted:
            delta = -delta
        current = self.verticalScrollBar().value()
        self.verticalScrollBar().setValue(current - delta)
        event.accept()

    def set_wheel_inverted(self, inverted: bool):
        self._wheel_inverted = inverted

    def is_wheel_inverted(self) -> bool:
        return self._wheel_inverted

    # ========== 列数管理 ==========
    def column_count(self):
        return self._column_count

    def set_column_count(self, count):
        count = max(1, count)
        if count != self._column_count:
            self._column_count = count
            self._layout_calc = ColumnLayoutCalculator(self._column_count, item_height=160)
            self.updateGeometries()
            self.viewport().update()

    # ========== 必须重写的虚函数 ==========
    def horizontalOffset(self) -> int:
        return 0

    def verticalOffset(self) -> int:
        return self._scroll_offset

    def isIndexHidden(self, index: QModelIndex) -> bool:
        return False

    def leaveEvent(self, event):
        self._last_mouse_pos = QPoint(-1, -1)
        self.viewport().update()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        self._last_mouse_pos = event.position().toPoint()
        self.viewport().update()
        super().mouseMoveEvent(event)

    def moveCursor(self, cursor_action, modifiers):
        if not self.model() or self.model().rowCount() == 0:
            return QModelIndex()

        current = self.currentIndex()
        if not current.isValid():
            return self.model().index(0, 0)

        visual_row = current.row() // self._column_count
        visual_col = current.row() % self._column_count

        if cursor_action == QAbstractItemView.CursorAction.MoveUp:
            visual_row -= 1
        elif cursor_action == QAbstractItemView.CursorAction.MoveDown:
            visual_row += 1
        elif cursor_action == QAbstractItemView.CursorAction.MoveLeft:
            visual_col -= 1
            if visual_col < 0:
                visual_row -= 1
                visual_col = self._column_count - 1
        elif cursor_action == QAbstractItemView.CursorAction.MoveRight:
            visual_col += 1
            if visual_col >= self._column_count:
                visual_row += 1
                visual_col = 0
        elif cursor_action == QAbstractItemView.CursorAction.MoveHome:
            visual_row = 0
            visual_col = 0
        elif cursor_action == QAbstractItemView.CursorAction.MoveEnd:
            last_row = (self.model().rowCount() - 1) // self._column_count
            last_col = (self.model().rowCount() - 1) % self._column_count
            visual_row = last_row
            visual_col = last_col
        else:
            return QModelIndex()

        if visual_row < 0 or visual_col < 0:
            return QModelIndex()

        new_row = visual_row * self._column_count + visual_col
        if new_row >= self.model().rowCount():
            return QModelIndex()

        return self.model().index(new_row, 0)

    def indexAt(self, point: QPoint) -> QModelIndex:
        if not self.model() or self.model().rowCount() == 0:
            return QModelIndex()

        if point.x() < self._layout_calc.margin or point.y() < self._layout_calc.margin:
            return QModelIndex()

        content_x = point.x() - self._layout_calc.margin
        content_y = point.y() - self._layout_calc.margin + self._scroll_offset

        available_width = (
            self.viewport().width() -
            2 * self._layout_calc.margin -
            (self._column_count - 1) * self._layout_calc.spacing
        )
        if available_width <= 0:
            return QModelIndex()

        base_width = available_width // self._column_count
        remainder = available_width % self._column_count

        col = -1
        x_acc = 0
        for c in range(self._column_count):
            w = base_width + (1 if c < remainder else 0)
            if x_acc <= content_x < x_acc + w:
                col = c
                break
            x_acc += w + self._layout_calc.spacing
        if col == -1:
            return QModelIndex()

        row_stride = self._layout_calc.item_height + self._layout_calc.spacing
        if content_y < 0:
            return QModelIndex()
        grid_row = content_y // row_stride
        y_in_row = content_y % row_stride
        if y_in_row >= self._layout_calc.item_height:
            return QModelIndex()

        index_row = grid_row * self._column_count + col
        if index_row >= self.model().rowCount():
            return QModelIndex()

        return self.model().index(index_row, 0)

    def visualRect(self, index: QModelIndex) -> QRect:
        if not index.isValid() or not self.model():
            return QRect()
        rects = self._layout_calc.compute_rects(
            self.model(), self.viewport().rect(), self._scroll_offset
        )
        return rects.get(index, QRect())

    def scrollTo(self, index, hint=QAbstractItemView.ScrollHint.EnsureVisible):
        if not index.isValid() or not self.model():
            return

        rect = self.visualRect(index)  #type: ignore[arg-type]
        if rect.isNull():
            return

        viewport_rect = self.viewport().rect()
        target = self._scroll_offset

        if rect.top() < 0:
            target += rect.top()
        elif rect.bottom() > viewport_rect.height():
            target += rect.bottom() - viewport_rect.height()

        target = max(0, target)
        self.verticalScrollBar().setValue(target)
        self.viewport().update()

    def setSelection(self, rect: QRect, command: QItemSelectionModel.SelectionFlag):
        """框选实现，使用正确的 flags 类型。"""
        if not self.model() or not self.selectionModel():
            return

        rects = self._layout_calc.compute_rects(
            self.model(), self.viewport().rect(), self._scroll_offset
        )

        selected_indexes = []
        for index, item_rect in rects.items():
            if item_rect.intersects(rect):
                selected_indexes.append(index)

        if selected_indexes:
            selection = QItemSelection()
            for idx in selected_indexes:
                selection.select(idx, idx)
            self.selectionModel().select(selection, command)

    def visualRegionForSelection(self, selection) -> QRegion:
        region = QRegion()
        for index in selection.indexes():
            rect = self.visualRect(index)
            if not rect.isEmpty():
                region += QRegion(rect)
        return region

    def scrollContentsBy(self, dx, dy):
        """滚动条滚动时更新偏移量（不再设置滚动条，避免递归）。"""
        if not self.model():
            return
        max_offset = max(0, self._layout_calc.total_height(self.model()) - self.viewport().height())
        self._scroll_offset += dy
        self._scroll_offset = max(0, min(self._scroll_offset, max_offset))
        self.viewport().update()

    def updateGeometries(self):
        super().updateGeometries()
        if self.model():
            total_height = self._layout_calc.total_height(self.model())
            viewport_height = self.viewport().height()
            max_offset = max(0, total_height - viewport_height)
            self.verticalScrollBar().setRange(0, max_offset)
            self.verticalScrollBar().setPageStep(viewport_height)
            self.verticalScrollBar().setSingleStep(20)

            if self._scroll_offset > max_offset:
                self._scroll_offset = max_offset
            self._scroll_offset = max(0, self._scroll_offset)
            self.verticalScrollBar().setValue(self._scroll_offset)
            self.viewport().update()

    # ========== 绘制 ==========
    def paintEvent(self, event):
        if not self.model():
            return

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rects = self._layout_calc.compute_rects(
            self.model(), self.viewport().rect(), self._scroll_offset
        )

        delegate = self.itemDelegate()
        if delegate is None:
            delegate = self.itemDelegate()

        for index, rect in rects.items():
            option = QStyleOptionViewItem()
            option.rect = rect
            option.widget = self
            option.state = QStyle.StateFlag.State_Enabled

            if self.selectionModel() and self.selectionModel().isSelected(index):
                option.state |= QStyle.StateFlag.State_Selected
            if self.currentIndex() == index:
                option.state |= QStyle.StateFlag.State_HasFocus

            if self._last_mouse_pos is not None and rect.contains(self._last_mouse_pos):
                option.state |= QStyle.StateFlag.State_MouseOver

            delegate.paint(painter, option, index)

        painter.end()

    # ========== 鼠标交互 ==========
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.model():
            point = event.position().toPoint()
            index = self.indexAt(point)
            if index.isValid():
                self.setCurrentIndex(index)
                self.selectionModel().select(
                    index,
                    self.selectionModel().SelectionFlag.ClearAndSelect
                )
            else:
                self.clearSelection()
                self.setCurrentIndex(QModelIndex())
            self.viewport().update()
        super().mousePressEvent(event)  # 基类会调用 setSelection 等，现在已实现

    # ========== 模型变化处理 ==========
    def setModel(self, model):
        super().setModel(model)
        self._scroll_offset = 0
        self.clearSelection()
        self.setCurrentIndex(QModelIndex())
        self.updateGeometries()
        self.viewport().update()

    def dataChanged(self, top_left, bottom_right, roles=None):
        super().dataChanged(top_left, bottom_right, roles)
        self.updateGeometries()

    def rowsInserted(self, parent, start, end):
        super().rowsInserted(parent, start, end)
        self.updateGeometries()

    def rowsAboutToBeRemoved(self, parent, start, end):
        super().rowsAboutToBeRemoved(parent, start, end)
        self.updateGeometries()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateGeometries()
