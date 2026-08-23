#
""""""

from PySide6.QtCore import Qt, QRect
from PySide6.QtWidgets import QLayout


class SquareLayout(QLayout):
    """
    让所有子部件保持正方形的布局。

    方向：
        - Qt.Orientation.Vertical：垂直排列，高度决定宽度（默认）
        - Qt.Orientation.Horizontal：水平排列，宽度决定高度

    用法：
        layout = SquareLayout(Qt.Orientation.Vertical)
        layout.addWidget(button)
        parent.setLayout(layout)
    """

    def __init__(self, orientation=Qt.Orientation.Vertical, parent=None):
        super().__init__(parent)
        self._orientation = orientation
        self._items = []  # 存储 (widgets, stretch) 元组
        self._spacing = 5
        self._margins = (5, 5, 5, 5)

    # ----- 添加/移除部件 -----
    def addItem(self, item):
        """QLayout 要求的接口，添加子项"""
        self._items.append(item)

    def addWidget(self, widget, stretch=0, alignment=Qt.AlignmentFlag.AlignCenter):
        """添加部件，可以指定伸缩因子和对齐方式（对齐暂未完全实现）"""
        self.addChildWidget(widget)
        item = QLayoutItemWrapper(widget)
        item._stretch = stretch
        item._alignment = alignment
        self._items.append(item)
        self.invalidate()

    def removeWidget(self, widget):
        """移除部件"""
        for i, item in enumerate(self._items):
            if item.widget() is widget:
                self._items.pop(i)
                self.removeItem(item)
                break
        self.invalidate()

    # ----- 尺寸信息 -----
    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            self.invalidate()
            return item
        return None

    def spacing(self):
        return self._spacing

    def setSpacing(self, spacing):
        self._spacing = spacing
        self.invalidate()

    # ----- 布局核心：计算子部件位置和大小 -----
    def setGeometry(self, rect):
        """重写此方法，实际布置子部件"""
        super().setGeometry(rect)

        if not self._items:
            return

        # 可用内部矩形（去掉 margins）
        left, top, right, bottom = self.getContentsMargins()
        inner = rect.adjusted(left, top, -right, -bottom)
        if inner.width() <= 0 or inner.height() <= 0:
            return

        n = len(self._items)
        total_spacing = self._spacing * (n - 1) if n > 1 else 0

        if self._orientation == Qt.Orientation.Vertical:
            # 高度决定宽度：每个部件高度 = (总内部高度 - 间距) / n
            item_h = (inner.height() - total_spacing) // n
            item_w = item_h  # 正方形
            # 防止宽度超出内部宽度
            if item_w > inner.width():
                item_w = inner.width()
                item_h = item_w
            # 水平居中
            x = inner.x() + (inner.width() - item_w) // 2
            y = inner.y()
        else:  # Horizontal
            # 宽度决定高度：每个部件宽度 = (总内部宽度 - 间距) / n
            item_w = (inner.width() - total_spacing) // n
            item_h = item_w
            if item_h > inner.height():
                item_h = inner.height()
                item_w = item_h
            # 垂直居中
            x = inner.x()
            y = inner.y() + (inner.height() - item_h) // 2

        # 摆放每个部件
        for i, item in enumerate(self._items):
            if self._orientation == Qt.Orientation.Vertical:
                pos_y = y + i * (item_h + self._spacing)
                item.setGeometry(QRect(x, pos_y, item_w, item_h))
            else:
                pos_x = x + i * (item_w + self._spacing)
                item.setGeometry(QRect(pos_x, y, item_w, item_h))

    # ----- 尺寸提示 -----
    def sizeHint(self):
        # 简单返回一个默认正方形大小，并不精确
        return self.minimumSize()

    def minimumSize(self):
        # 返回最小尺寸：每个子部件至少 0 大小，加上边距
        left, top, right, bottom = self.getContentsMargins()
        return self._square_size_for_items(0)

    def _square_size_for_items(self, per_item_size):
        """根据期望的单个正方形边长，计算布局所需的总尺寸（考虑间距和边距）"""
        n = len(self._items)
        if n == 0:
            total_spacing = 0
        else:
            total_spacing = self._spacing * (n - 1)
        left, top, right, bottom = self.getContentsMargins()
        if self._orientation == Qt.Orientation.Vertical:
            width = per_item_size + left + right
            height = per_item_size * n + total_spacing + top + bottom
        else:
            width = per_item_size * n + total_spacing + left + right
            height = per_item_size + top + bottom
        return self._qsize(width, height)

    def hasHeightForWidth(self):
        return self._orientation == Qt.Orientation.Horizontal

    def heightForWidth(self, width):
        if self._orientation != Qt.Orientation.Horizontal:
            return -1
        # 根据宽度反推正方形边长，再计算所需高度
        left, right, _, _ = self.getContentsMargins()
        inner_width = width - left - right
        n = len(self._items)
        if n == 0:
            item_w = 0
        else:
            item_w = (inner_width - self._spacing * (n - 1)) // n
        # 高度 = 正方形边长 + 上下边距
        top, bottom = self.getContentsMargins()[2:]
        return max(0, item_w) + top + bottom

    # 为了QSize的跨版本兼容
    def _qsize(self, w, h):
        from PySide6.QtCore import QSize
        return QSize(w, h)


# 内部辅助，包装 QWidget 为 QLayoutItem
class QLayoutItemWrapper:
    """简易适配器，满足 QLayout 对 item 的要求"""

    def __init__(self, widget):
        self._widget = widget
        self._stretch = 0
        self._alignment = Qt.AlignmentFlag.AlignCenter

    def widget(self):
        return self._widget

    def setGeometry(self, rect):
        self._widget.setGeometry(rect)

    def sizeHint(self):
        return self._widget.sizeHint()

    def minimumSize(self):
        return self._widget.minimumSize()

    def expandingDirections(self):
        return Qt.Orientation(0)

    def isEmpty(self):
        return False

    def hasHeightForWidth(self):
        return False

    def heightForWidth(self, w):
        return -1