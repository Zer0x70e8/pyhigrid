# titlebar.py
""""""

from traceback import format_exc

from PySide6.QtWidgets import (
    QPushButton, QWidget, QHBoxLayout, QVBoxLayout,
)
from PySide6.QtCore import Qt, Signal

from ..widget.title_and_icon import TitleAndIcon
from ..widget.top_window_action_buttons_widget import TopWindowActionButtonsWidget
from ..widget.tool_bar_widget import (
    ToolBar, SearchBarLayoutPlaceholder
)


class _ToolBar(ToolBar):
    """内部工具栏：包含图片按钮、搜索占位符、更多按钮，并负责搜索栏展开/关闭动画"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleToolBar")

        # # 图标路径
        # icon_path = "E:/myCode/py/pyhigrid/src/pyhigrid/resources/icon"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 相薄按钮
        self.album_button: QPushButton = QPushButton(self)
        self.album_button.setObjectName("AlbumButton")
        # self.image_button.setIcon(QIcon(f"{icon_path}/image_icon.png"))
        # self.image_button.setIconSize(QSize(48, 48))
        self.album_button.setFixedSize(48, 48)

        # 搜索占位符
        self.placeholder_widget = SearchBarLayoutPlaceholder(self)
        self.placeholder_widget.setObjectName("SearchPlaceholder")
        self.placeholder_widget.setFixedSize(48, 48)
        # 占位符点击 → 展开搜索
        self.placeholder_widget.clicked.connect(self.expand_search)

        # 更多按钮
        self.more_button = QPushButton()
        self.more_button.setObjectName("MoreButton")
        # self.more_button.setIcon(QIcon(f"{icon_path}/more_icon.png"))
        # self.more_button.setIconSize(QSize(48, 48))
        self.more_button.setFixedSize(48, 48)

        layout.addWidget(self.album_button)
        layout.addStretch()
        layout.addWidget(self.placeholder_widget)
        layout.addWidget(self.more_button)

        # 将占位符实例赋给基类的 placeholder 属性（基类通过 setter 保存引用）
        self.placeholder = self.placeholder_widget

class TitleBar(QWidget):
    search = Signal(dict)
    btn_more_clicked = Signal()
    btn_album_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.title = None
        self.action_widget = None
        self.tool_bar = None
        self.search_bar = None

        self.row_layout = None

        self.logger = None

        self._first_refresh = False

        self.setup_()
        self.setup_ui()

    def setup(self, logger):
        self.logger = logger

        self.setup_signal()

    def setup_(self):
        self.setFixedHeight(112)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 0)

        # 窗口操作按钮（浮动叠加层）
        self.action_widget = TopWindowActionButtonsWidget(self)

        # 标题图标与文字
        self.title = TitleAndIcon(self)

        # 使用封装了搜索栏功能的工具栏
        self.tool_bar = _ToolBar(self)

        # 水平布局：标题 + 工具栏（自动拉伸）
        self.row_layout = QHBoxLayout()
        self.row_layout.setContentsMargins(0, 0, 8, 0)
        self.row_layout.setSpacing(8)
        self.row_layout.addWidget(self.title)
        self.row_layout.addWidget(self.tool_bar)

        layout.addWidget(self.action_widget)
        layout.addLayout(self.row_layout)
        layout.addStretch()

    def setup_signal(self):
        def connector(signal, slot):
            try:
                signal.connect(slot)
            except AttributeError:
                self.logger.warning(
                    format_exc()
                )

        connector(self.tool_bar.album_button.clicked, self.btn_album_clicked)
        connector(self.tool_bar.more_button.clicked, self.btn_more_clicked)

    def showEvent(self, event):
        super().showEvent(event)

        if not self._first_refresh:
            self.title.set_icon("")
            self.title.set_title("All")

            self._first_refresh = True


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QWidget

    app = QApplication(sys.argv)

    window = QWidget()
    window.setAttribute(Qt.WA_StyledBackground, True)
    layout_ = QVBoxLayout()
    t = TitleBar(window)
    layout_.addWidget(t)
    layout_.addStretch()
    window.setLayout(layout_)
    window.show()
    exit(app.exec())