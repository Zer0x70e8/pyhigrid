# slide_up_scroll_container.py
""""""

from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout

class SlideUpScrollContainer(QScrollArea):
    """
    通用容器：
    - 外层滚动区域（自身）仅在上拉菜单显示时产生滚动条
    - 内层滚动区域始终填满视口，用于显示任意尺寸的核心内容
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 内部根 widget
        self._root = QWidget()
        self._root_layout = QVBoxLayout(self._root)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # 内层滚动区域（承载核心内容）
        self.inner_scroll = QScrollArea()
        self.inner_scroll.setWidgetResizable(False)
        self._root_layout.addWidget(self.inner_scroll)

        # 菜单容器（默认高度 0）
        self._menu_container = QWidget()
        self._menu_container.setFixedHeight(0)
        self._menu_layout = QVBoxLayout(self._menu_container)
        self._menu_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.addWidget(self._menu_container)

        self.setWidget(self._root)

        # 监听视口大小变化，自动同步内层高度
        self.viewport().installEventFilter(self)
        self.inner_scroll.viewport().installEventFilter(self)


        # 初始化尺寸
        QTimer.singleShot(0, self._sync_sizes)

    def set_central_widget(self, widget: QWidget):
        """设置内层滚动区域的内容组件"""
        self.inner_scroll.setWidget(widget)

    def set_menu_widget(self, widget: QWidget):
        """替换菜单容器内的内容"""
        # 清空原有内容
        while self._menu_layout.count():
            item = self._menu_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._menu_layout.addWidget(widget)

    def show_menu(self, height: int = 200):
        """显示菜单，可指定高度"""
        self._menu_container.setFixedHeight(height)
        self._sync_sizes()

    def hide_menu(self):
        """隐藏菜单"""
        self._menu_container.setFixedHeight(0)
        self._sync_sizes()

    def toggle_menu(self, height: int = 200):
        """切换菜单显示状态"""
        if self._menu_container.height() > 0:
            self.hide_menu()
        else:
            self.show_menu(height)
            

    def _sync_sizes(self):
        """核心同步：让内层滚动区域高度 = 视口高度，并更新容器总高度"""
        vp = self.viewport()
        if not vp:
            return
        vp_width = vp.width()
        vp_height = vp.height()
        self.inner_scroll.setFixedHeight(vp_height)
        total_height = vp_height + self._menu_container.height()
        self._root.setFixedSize(vp_width, total_height)

    def eventFilter(self, obj, event):
        # 原有：外层视口大小变化时同步尺寸
        if obj is self.viewport() and event.type() == QEvent.Type.Resize:
            self._sync_sizes()
            return super().eventFilter(obj, event)

        # 新增：内层滚动区域视口的滚轮事件拦截
        if obj is self.inner_scroll.viewport() and event.type() == QEvent.Type.Wheel:
            # 只有在菜单可见时才拦截
            if self._menu_container.height() > 0:
                # 滚轮向上滚动 (angleDelta().y() > 0) 表示“上划”，优先关闭菜单
                if event.angleDelta().y() > 0:
                    self.hide_menu()
                    return True  # 事件已处理，不再传递给内层滚动区域
                # 向下滚动时，可以保持菜单不关闭，或者根据需求也关闭，这里选择不处理
                # 让内层正常滚动，但菜单仍保持打开（符合一些应用的交互）
            # 菜单不可见，或方向不符合，正常传递给内层滚动区域
            return super().eventFilter(obj, event)

        return super().eventFilter(obj, event)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QToolBar, QLabel, QPushButton
    )

    def create_central_widget():
        """内层内容：浅蓝色背景，高度远超视口，测试内层滚动"""
        w = QWidget()
        w.setStyleSheet("background-color: #d0e4f5;")
        layout = QVBoxLayout(w)
        text = "内层滚动区域\n" * 50
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(label)
        return w

    def create_menu_widget():
        """上拉菜单：珊瑚色背景，包含简单按钮"""
        w = QWidget()
        w.setStyleSheet("background-color: #f08080;")
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("这是菜单区域", alignment=Qt.AlignmentFlag.AlignCenter))
        for i in range(3):
            layout.addWidget(QPushButton(f"菜单项 {i+1}"))
        return w

    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("SlideUpScrollContainer 测试")
            self.resize(500, 400)

            self.container = SlideUpScrollContainer()
            self.setCentralWidget(self.container)
            self.container.set_central_widget(create_central_widget())
            self.container.set_menu_widget(create_menu_widget())

            toolbar = QToolBar("控制")
            self.addToolBar(toolbar)
            toolbar.addAction("切换菜单").triggered.connect(
                lambda: self.container.toggle_menu(200)
            )
            toolbar.addAction("显示菜单").triggered.connect(
                lambda: self.container.show_menu(200)
            )
            toolbar.addAction("隐藏菜单").triggered.connect(
                lambda: self.container.hide_menu()
            )

    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    sys.exit(app.exec())
