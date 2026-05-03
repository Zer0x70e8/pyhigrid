# titlebar.py
""""""

# noinspection PyUnusedImports
from PySide6.QtWidgets import (
    QToolBar, QLabel, QPushButton, QWidget, QHBoxLayout, QVBoxLayout,
    QSizePolicy, QLineEdit
)
# noinspection PyUnusedImports
from PySide6.QtGui import QAction, QIcon, QFont
# noinspection PyUnusedImports
from PySide6.QtCore import Qt, QSize, QEvent

# 导入 ToolBar 及其相关部件
if __name__ == "__main__":
    from pyhigrid.ui.gui.widget.title_and_icon import TitleAndIcon
    from pyhigrid.ui.gui.widget.top_window_action_buttons_widget import (
        TopWindowActionButtonsWidget
    )
    from pyhigrid.ui.gui.widget.tool_bar_widget import (
        ToolBar, SearchBarLayoutPlaceholder
)
else:
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

        # 图片按钮
        self.image_button = QPushButton()
        self.image_button.setObjectName("ImageButton")
        # self.image_button.setIcon(QIcon(f"{icon_path}/image_icon.png"))
        # self.image_button.setIconSize(QSize(48, 48))
        self.image_button.setFixedSize(48, 48)

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

        layout.addWidget(self.image_button)
        layout.addStretch()
        layout.addWidget(self.placeholder_widget)
        layout.addWidget(self.more_button)

        # 将占位符实例赋给基类的 placeholder 属性（基类通过 setter 保存引用）
        self.placeholder = self.placeholder_widget

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.title = None
        self.action_widget = None
        self.tool_bar = None
        self._first_refresh = False
        self.search_bar = _ToolBar(self)

        self.row_layout = None

        self.setup_()
        self.setup_ui()

    def setup_(self):
        self.setFixedHeight(112)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 24, 8, 0)

        # 窗口操作按钮（浮动叠加层）
        self.action_widget = TopWindowActionButtonsWidget(self)

        # 标题图标与文字
        self.title = TitleAndIcon(self)

        # 使用封装了搜索栏功能的工具栏
        self.tool_bar = _ToolBar(self)

        # 水平布局：标题 + 工具栏（自动拉伸）
        self.row_layout = QHBoxLayout()
        self.row_layout.setContentsMargins(0, 0, 0, 0)
        self.row_layout.setSpacing(8)
        self.row_layout.addWidget(self.title)
        self.row_layout.addWidget(self.tool_bar)

        layout.addLayout(self.row_layout)
        layout.addStretch()

        if __debug__:
            self.setStyleSheet("""
                TitleBar {
                    background-color: #2c3e50;
                    border: none;
                }
                #TitleToolBar {
                    background-color: transparent;
                    border: none;
                }
                
                #SearchCloseBtn, #SearchCloseBtn, #ImageButton, #MoreButton, #SearchPlaceholder {
                    min-width: 48px;
                    min-height: 48px;
                    max-width: 48px;
                    max-height: 48px;
                    border-radius: 24px;
                    border: none;
                    background-color: transparent;
                }
                #SearchCloseBtn, #ImageButton:hover, #MoreButton:hover, #SearchPlaceholder:hover {
                    background-color: rgba(255,255,255,0.1);
                }
                /* 搜索栏本身 */
                #searchBar {
                    background-color: white;
                    border-radius: 4px;
                }
                #searchLineEdit {
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 14px;
                    background: white;
                }
                #searchCloseBtn {
                    min-width: 24px; max-width: 24px;
                    min-height: 24px; max-height: 24px;
                    border: none; background: transparent;
                    font-size: 14px; color: #888;
                }
                #searchCloseBtn:hover {
                    color: #333; background-color: #eee;
                    border-radius: 4px;
                }
            """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 仅需要更新浮动操作按钮的位置
        if self.action_widget:
            self.action_widget.setGeometry(
                0, self.action_widget.window_border_top_right_radius,
                self.width(), self.action_widget.height()
            )

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