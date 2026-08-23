#
""""""

from PySide6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout,
    QSplitter, QApplication, QPushButton
)
from PySide6.QtCore import Qt

# if __package__ is None or __package__ == '':
try:
    from ..widgets.blur_overlay_label import BlurLabel
    from ..widgets.collapsible_group_box import CollapsibleGroupBox
except ImportError:
    # BlurLabel = QWidget
    from albuswall.ui.gui.widgets.blur_overlay_label import BlurLabel
    from albuswall.ui.gui.widgets.collapsible_group_box import CollapsibleGroupBox


class Setting(QWidget):
    """Setting widgets: standalone window or embedded child."""

    def __init__(self,
                 parent=None,
                 auto_setup=True,
                 as_independent=False
                 ):
        super().__init__(parent)
        self._as_independent = as_independent

        self._setup()

        self.background = None
        # 水平分割器
        self.splitter = None
        # 左侧导航区域
        self.nav_scroll = None # 左侧滚动区域
        self.nav_widget = None  # 左侧内部容器（用于放置按钮列表）
        self.nav_layout = None  # 左侧内部容器（用于放置按钮列表）
        # 右侧内容区域
        self.content_scroll = None  # 右侧滚动区域
        self.content_widget = None  # 右侧内部容器（用于放置实际内容）
        self.content_layout = None  # 右侧内部容器（用于放置实际内容）

        if auto_setup:
            self.setup()

    def _setup(self):
        self.setObjectName("SettingMain")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setup(self):
        self._setup_ui()

    def _setup_ui(self):
        # 背景
        self.background = BlurLabel(self)

        # 分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---- 左侧导航区域 ----
        self.nav_scroll = QScrollArea()
        self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 左侧内部容器（将来放置跳转按钮）
        self.nav_widget = QWidget()
        self.nav_scroll.setWidget(self.nav_widget)
        self.nav_layout = QVBoxLayout(self.nav_widget)
        self.nav_widget.setLayout(self.nav_layout)

        # ---- 右侧内容区域 ----
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 右侧内部容器（将来动态替换或填充内容）
        self.content_widget = QWidget()
        self.content_scroll.setWidget(self.content_widget)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_widget.setLayout(self.content_layout)

        # 加入分割器
        self.splitter.addWidget(self.nav_scroll)
        self.splitter.addWidget(self.content_scroll)
        self.splitter.setSizes([100, 400])
        self.splitter.setCollapsible(1, False)

        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)

    def scroll_to_widget_top(self, target_widget):
        # 计算目标控件左上角在内容容器里的坐标
        pos = target_widget.mapTo(self.content_scroll.widget(), target_widget.rect().topLeft())
        # 设置垂直滚动条
        self.content_scroll.verticalScrollBar().setValue(pos.y())
        # 如果有水平滚动
        # self.content_scroll.horizontalScrollBar().setValue(pos.x())

    def add_jump_button(self, target_widget: QWidget, obj_name: str):
        btn = QPushButton(self.nav_widget)
        btn.setObjectName(obj_name)
        jump_handler = lambda: self.scroll_to_widget_top(target_widget)
        btn.clicked.connect(jump_handler)
        self.nav_layout.addWidget(btn)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.background is not None:
            self.background.setGeometry(self.geometry())
            self.background.lower()


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QLabel
    app = QApplication(sys.argv)
    window = Setting()

    l = QLabel("test\n"*150)
    window.content_layout.addWidget(l)
    l1 = QLabel("test1\n"*150)
    window.content_layout.addWidget(l1)
    l2 = QLabel("test2\n"*150)
    window.content_layout.addWidget(l2)
    window.add_jump_button(l1, "testLabel")

    window.show()
    sys.exit(app.exec())

