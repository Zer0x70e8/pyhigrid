import sys
from typing import cast

from PySide6.QtCore import Qt, QPoint, QEvent, QTimer
from PySide6.QtGui import QPixmap, QPainter, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QScrollArea, QWidget, QFileDialog,
    QVBoxLayout, QPushButton, QLabel, QSizePolicy, QToolBar
)

# ========== 原有的 ImageViewer（可缩放、可拖拽） ==========

class ImageViewer(QWidget):
    MIN_ZOOM = 0.1
    MAX_ZOOM = 10.0
    ZOOM_STEP = 0.1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self._zoom_factor = 1.0
        self._drag_global_start = QPoint()
        self._scroll_start_pos = QPoint()
        self._dragging = False
        self._scroll_area = None
        self.setMinimumSize(10, 10)

    def set_scroll_area(self, scroll_area):
        self._scroll_area = scroll_area

    def _start_drag(self, global_pos):
        self._drag_global_start = global_pos
        if self._scroll_area:
            h_bar = self._scroll_area.horizontalScrollBar()
            v_bar = self._scroll_area.verticalScrollBar()
            self._scroll_start_pos = QPoint(h_bar.value(), v_bar.value())
        self._dragging = True
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def _stop_drag(self):
        if self._dragging:
            self._dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)

    def eventFilter(self, watched, event):
        if not self._dragging:
            return super().eventFilter(watched, event)
        if event.type() == QEvent.Type.MouseMove:
            mouse_event = cast(QMouseEvent, event)
            global_pos = mouse_event.globalPosition().toPoint()
            delta = global_pos - self._drag_global_start
            if self._scroll_area:
                h_bar = self._scroll_area.horizontalScrollBar()
                v_bar = self._scroll_area.verticalScrollBar()
                h_bar.setValue(self._scroll_start_pos.x() - delta.x())
                v_bar.setValue(self._scroll_start_pos.y() - delta.y())
            return True
        elif event.type() == QEvent.Type.MouseButtonRelease:
            mouse_event = cast(QMouseEvent, event)
            if mouse_event.button() == Qt.MouseButton.LeftButton:
                self._stop_drag()
                return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._scroll_area:
            self._start_drag(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._stop_drag()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def load_pixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._zoom_factor = 1.0
        if not pixmap.isNull():
            self.resize(pixmap.size())
        else:
            self.resize(0, 0)
        self.update()

    def pixmap(self) -> QPixmap:
        return self._pixmap

    def zoom_factor(self) -> float:
        return self._zoom_factor

    def set_zoom_factor(self, factor: float):
        if self._pixmap.isNull():
            return
        factor = max(self.MIN_ZOOM, min(self.MAX_ZOOM, factor))
        if abs(factor - self._zoom_factor) < 1e-6:
            return
        self._zoom_factor = factor
        new_size = (self._pixmap.size().toSizeF() * self._zoom_factor).toSize()
        self.resize(new_size)
        self.update()

    def zoom_in(self, step: float = ZOOM_STEP):
        self.set_zoom_factor(self._zoom_factor + step)

    def zoom_out(self, step: float = ZOOM_STEP):
        self.set_zoom_factor(self._zoom_factor - step)

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self._pixmap.isNull():
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.scale(self._zoom_factor, self._zoom_factor)
            painter.drawPixmap(0, 0, self._pixmap)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            event.ignore()


# ========== 外层滚动容器的内部布局 ==========

class OuterContent(QWidget):
    """容器：上方是内层滚动区域（大小=窗口），下方是可显示的菜单"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- 内层滚动区域（承载 ImageViewer） ---
        self.inner_scroll = QScrollArea()
        self.inner_scroll.setWidgetResizable(False)   # 让内容自由决定尺寸
        self.inner_scroll.setStyleSheet("QScrollArea { border: 2px solid blue; }")
        layout.addWidget(self.inner_scroll)

        # --- 菜单区域（初始不可见） ---
        self.menu_container = QWidget()
        self.menu_container.setFixedHeight(0)
        self.menu_container.setStyleSheet("background: #f0f0f0; border: 2px solid red;")
        menu_layout = QVBoxLayout(self.menu_container)
        menu_layout.addWidget(QLabel("这里是上拉菜单"))
        menu_layout.addWidget(QPushButton("菜单中的按钮"))
        menu_layout.addStretch()
        layout.addWidget(self.menu_container)

    def set_inner_height(self, h: int):
        """固定内层滚动区域的高度"""
        self.inner_scroll.setFixedHeight(h)

    def show_menu(self, height: int = 200):
        """显示菜单，设置菜单高度"""
        self.menu_container.setFixedHeight(height)

    def hide_menu(self):
        """隐藏菜单，高度归零"""
        self.menu_container.setFixedHeight(0)


# ========== 主窗口 ==========

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("嵌套滚动 + 图片查看器 + 上拉菜单")
        self.resize(800, 600)

        # 外层滚动区域（填满窗口）
        self.outer_scroll = QScrollArea()
        self.outer_scroll.setWidgetResizable(False)
        self.outer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.outer_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 创建内部容器
        self.outer_content = OuterContent()
        self.outer_scroll.setWidget(self.outer_content)
        self.setCentralWidget(self.outer_scroll)

        # 创建图片查看器并放入内层滚动区域
        self.image_viewer = ImageViewer()
        self.outer_content.inner_scroll.setWidget(self.image_viewer)
        self.image_viewer.set_scroll_area(self.outer_content.inner_scroll)

        # 监听视口大小变化，同步内层高度
        self.outer_scroll.viewport().installEventFilter(self)

        # 工具栏：打开图片、显示/隐藏菜单
        toolbar = self.addToolBar("工具")
        open_action = toolbar.addAction("打开图片")
        open_action.triggered.connect(self.open_image)

        self.menu_btn = QPushButton("打开菜单")
        self.menu_btn.setCheckable(True)
        self.menu_btn.toggled.connect(self.on_toggle_menu)
        toolbar.addWidget(self.menu_btn)

        # 初始化尺寸
        QTimer.singleShot(0, self.sync_sizes)

    def open_image(self):
        """选择图片并加载到 ImageViewer"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                print("无法加载图片:", file_path)
                return
            self.image_viewer.load_pixmap(pixmap)

    def eventFilter(self, obj, event):
        if obj is self.outer_scroll.viewport() and event.type() == QEvent.Type.Resize:
            self.sync_sizes()
        return super().eventFilter(obj, event)

    def sync_sizes(self):
        """同步内层高度 = 视口高度，并更新外层容器的总尺寸"""
        vp_size = self.outer_scroll.viewport().size()
        self.outer_content.set_inner_height(vp_size.height())
        # 容器总高度 = 内层高度 + 菜单高度
        total_height = vp_size.height() + self.outer_content.menu_container.height()
        self.outer_content.setFixedSize(vp_size.width(), total_height)

    def on_toggle_menu(self, checked):
        if checked:
            self.outer_content.show_menu()
            self.menu_btn.setText("关闭菜单")
        else:
            self.outer_content.hide_menu()
            self.menu_btn.setText("打开菜单")
        self.sync_sizes()  # 更新外层滚动区域

    def showEvent(self, event):
        super().showEvent(event)
        self.sync_sizes()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())