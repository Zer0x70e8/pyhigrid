import sys
from PySide6.QtCore import (
    QAbstractItemModel, QModelIndex, QRect, Qt, QSize, QPoint, QItemSelection
)
from PySide6.QtGui import QPainter, QColor, QRegion
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QAbstractItemView,
    QStyledItemDelegate, QStyleOptionViewItem,
    QStyle, QVBoxLayout, QWidget
)

# ---------- 1. 自定义 Model ----------
class SimpleModel(QAbstractItemModel):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self._data = data

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self._data[index.row()]
        return None

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid() or row < 0 or row >= len(self._data) or column != 0:
            return QModelIndex()
        return self.createIndex(row, column, None)

    def parent(self, index):
        return QModelIndex()

# ---------- 2. 自定义 Delegate ----------
class MyDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)

        if option.state & QStyle.State_Selected:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor("red"))
            painter.setPen(Qt.NoPen)
            rect = option.rect
            center = rect.topRight() + QPoint(-10, 10)
            painter.drawEllipse(center, 4, 4)
            painter.restore()

    def sizeHint(self, option, index):
        return QSize(100, 40)

# ---------- 3. 自定义 View ----------
class SimpleView(QAbstractItemView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._row_height = 40
        self.setItemDelegate(MyDelegate(self))
        self.verticalScrollBar().setRange(0, 0)
        self.horizontalScrollBar().setRange(0, 0)

    # ---- 必须实现的纯虚函数 ----
    def visualRect(self, index):
        if not index.isValid():
            return QRect()
        x = -self.horizontalOffset()
        y = index.row() * self._row_height - self.verticalOffset()
        return QRect(x, y, self.viewport().width(), self._row_height)

    def scrollTo(self, index, hint=QAbstractItemView.EnsureVisible):
        if not index.isValid():
            return
        y = index.row() * self._row_height
        current = self.verticalScrollBar().value()
        view_h = self.viewport().height()
        if y < current:
            self.verticalScrollBar().setValue(y)
        elif y + self._row_height > current + view_h:
            self.verticalScrollBar().setValue(y + self._row_height - view_h)
        self.viewport().update()

    def indexAt(self, point):
        row = (point.y() + self.verticalOffset()) // self._row_height
        model = self.model()
        if model and row >= 0 and row < model.rowCount():
            return model.index(row, 0)
        return QModelIndex()

    def horizontalOffset(self):
        return self.horizontalScrollBar().value()

    def verticalOffset(self):
        return self.verticalScrollBar().value()

    def isIndexHidden(self, index):
        return False

    def moveCursor(self, cursorAction, modifiers):
        model = self.model()
        if not model:
            return QModelIndex()
        current = self.currentIndex()
        row = current.row() if current.isValid() else -1
        if cursorAction == QAbstractItemView.MoveDown:
            row = min(row + 1, model.rowCount() - 1)
        elif cursorAction == QAbstractItemView.MoveUp:
            row = max(row - 1, 0)
        elif cursorAction == QAbstractItemView.MoveHome:
            row = 0
        elif cursorAction == QAbstractItemView.MoveEnd:
            row = model.rowCount() - 1
        else:
            return QModelIndex()
        return model.index(row, 0)

    def setSelection(self, rect, command):
        model = self.model()
        if not model:
            return
        selection = self.selectionModel()
        first_row = (rect.top() + self.verticalOffset()) // self._row_height
        last_row = (rect.bottom() + self.verticalOffset()) // self._row_height
        first_row = max(0, first_row)
        last_row = min(model.rowCount() - 1, last_row)
        if first_row > last_row:
            return
        index_first = model.index(first_row, 0)
        index_last = model.index(last_row, 0)
        item_selection = QItemSelection(index_first, index_last)
        selection.select(item_selection, command)

    def visualRegionForSelection(self, selection):
        # 返回选中项的可视区域（所有选中项矩形的并集）
        region = QRegion()
        for index in selection.indexes():
            region = region.united(QRegion(self.visualRect(index)))
        return region

    # ---- 其他必要重写 ----
    def scrollContentsBy(self, dx, dy):
        self.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.model():
            self.updateScrollBars()
        self.viewport().update()

    def setModel(self, model):
        super().setModel(model)
        if model:
            self.updateScrollBars()
        else:
            self.verticalScrollBar().setRange(0, 0)
            self.horizontalScrollBar().setRange(0, 0)
        self.viewport().update()

    def updateScrollBars(self):
        model = self.model()
        if not model:
            return
        total_height = model.rowCount() * self._row_height
        view_h = self.viewport().height()
        self.verticalScrollBar().setRange(0, max(0, total_height - view_h))
        self.verticalScrollBar().setPageStep(view_h)
        self.horizontalScrollBar().setRange(0, 0)

    # ---- 绘制事件 ----
    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        model = self.model()
        if not model:
            return

        first_row = max(0, self.verticalOffset() // self._row_height)
        last_row = min(model.rowCount(),
                       (self.verticalOffset() + self.viewport().height()) // self._row_height + 1)

        for row in range(first_row, last_row):
            index = model.index(row, 0)
            option = QStyleOptionViewItem()
            option.rect = self.visualRect(index)
            option.state = QStyle.State_Enabled
            if self.selectionModel().isSelected(index):
                option.state |= QStyle.State_Selected
            option.widget = self

            delegate = self.itemDelegateForIndex(index)
            if delegate:
                delegate.paint(painter, option, index)

# ---------- 4. 主窗口 ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("自定义 View + Delegate + QSS 测试")

        data = [f"Item {i+1}" for i in range(20)]
        self.model = SimpleModel(data)

        self.view = SimpleView()
        self.view.setModel(self.model)

        self.view.setStyleSheet("""
            SimpleView {
                background: grey;
                spacing: 4px;
            }
            SimpleView::item {
                background: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin: 2px;
                padding-left: 10px;
                color: #333333;
            }
            SimpleView::item:selected {
                background: #cce8ff;
                border: 1px solid #4a90d9;
            }
        """)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.view)
        self.setCentralWidget(central)
        self.resize(400, 300)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())