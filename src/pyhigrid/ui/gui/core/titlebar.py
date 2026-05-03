#
""""""

# noinspection PyUnusedImports
from PySide6.QtWidgets import (
    QToolBar, QLabel, QPushButton, QWidget, QHBoxLayout, QVBoxLayout,
    QSizePolicy, QLineEdit
)
# noinspection PyUnusedImports
from PySide6.QtGui import QAction, QIcon, QFont
# noinspection PyUnusedImports
from PySide6.QtCore import Qt, QSize, QEvent, QPropertyAnimation, QRect, QEasingCurve

if __name__ == "__main__":
    from pyhigrid.ui.gui.widget.title_and_icon import TitleAndIcon
    from pyhigrid.ui.gui.widget.top_window_action_buttons_widget import (
        TopWindowActionButtonsWidget
    )
    from pyhigrid.ui.gui.widget.tool_bar_widget import (
        SearchBarLayoutPlaceholder, SearchBar
    )
else:
    from ..widget.title_and_icon import TitleAndIcon
    from ..widget.top_window_action_buttons_widget import TopWindowActionButtonsWidget
    from ..widget.tool_bar_widget import SearchBarLayoutPlaceholder, SearchBar


class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.title = None
        self.action_widget = None
        self.image_button = None
        self.more_button = None
        self.search_placeholder = None   # 搜索占位符
        self.search_bar = None           # 实际的搜索栏（动画目标）

        self._first_refresh = False

        # 动画状态
        self.is_expanded = False
        self._anim = None
        self._anim_target = None  # True=展开, False=关闭
        self._cached_placeholder_rect = None
        self._animation_enabled = True

        self.setup_()
        self.setup_ui()
        self.setup_search()

    def setup_(self):
        self.setFixedHeight(112)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 24, 8, 0)

        self.action_widget = TopWindowActionButtonsWidget(self)
        self.title = TitleAndIcon(self)

        # 原三个按钮：图片、搜索（占位符）、更多
        self.image_button = QPushButton(self)
        self.more_button = QPushButton(self)
        self.search_placeholder = SearchBarLayoutPlaceholder(self)   # 替换原来的 QPushButton

        self.image_button.setObjectName("ImageButton")
        self.more_button.setObjectName("MoreButton")
        self.search_placeholder.setObjectName("SearchPlaceholder")   # 样式可以沿用或新写

        # 图标设置
        icon_path = "E:/myCode/py/pyhigrid/src/pyhigrid/resources/icon"
        self.image_button.setIcon(QIcon(f"{icon_path}/image_icon.png"))
        self.more_button.setIcon(QIcon(f"{icon_path}/more_icon.png"))
        self.search_placeholder.setIcon(QIcon(f"{icon_path}/search_icon.png"))

        icon_size = QSize(48, 48)
        self.image_button.setIconSize(icon_size)
        self.more_button.setIconSize(icon_size)
        self.search_placeholder.setFixedSize(48, 48)   # 占位符尺寸

        # 第一行水平布局
        self.row_layout = QHBoxLayout()
        self.row_layout.setContentsMargins(0, 0, 0, 0)
        self.row_layout.setSpacing(8)
        self.row_layout.addWidget(self.title)
        self.row_layout.addWidget(self.image_button)
        self.row_layout.addStretch()
        self.row_layout.addWidget(self.search_placeholder)
        self.row_layout.addWidget(self.more_button)

        layout.addLayout(self.row_layout)
        layout.addStretch()

    def setup_search(self):
        """初始化搜索栏控件（先隐藏）"""
        self.search_bar = SearchBar(parent=self, placeholder=self.search_placeholder)
        self.search_bar.setObjectName("searchBar")
        self.search_bar.hide()

        # 信号连接
        self.search_bar.closed.connect(self.collapse_search)
        self.search_placeholder.clicked.connect(self.expand_search)

    # ---------- 展开/关闭入口 ----------
    def expand_search(self):
        if self.is_expanded:
            return
        self.is_expanded = True

        # 缓存占位符几何
        self._cached_placeholder_rect = self.search_placeholder.geometry()

        # 隐藏普通按钮和占位符
        self.image_button.hide()
        self.more_button.hide()
        self.search_placeholder.hide()

        # 计算目标区域：从 image_button 的左侧到 more_button 的右侧（即整个按钮区）
        target_rect = QRect(
            self.image_button.geometry().left(),
            self.search_placeholder.geometry().top(),
            self.more_button.geometry().right() - self.image_button.geometry().left(),
            self.search_placeholder.height()
        )

        self.search_bar.show()
        self.search_bar.raise_()
        self.search_bar.setGeometry(self._cached_placeholder_rect)  # 动画起点

        self._start_transition(target_rect, target_is_expanded=True)

    def collapse_search(self):
        if not self.is_expanded:
            return
        self.is_expanded = False

        if self._cached_placeholder_rect is None:
            self._cached_placeholder_rect = self.search_placeholder.geometry()

        self._start_transition(self._cached_placeholder_rect, target_is_expanded=False)

    # ---------- 动画逻辑（直接借鉴 ToolBar） ----------
    def _start_transition(self, target_rect: QRect, target_is_expanded: bool):
        if self._anim is None:
            self._anim = QPropertyAnimation(self.search_bar, b"geometry")
            self._anim.setDuration(250)
            self._anim.setEasingCurve(QEasingCurve.OutCubic)
            self._anim.finished.connect(self._on_anim_finished)

        if self._anim.state() == QPropertyAnimation.Running:
            self._anim.stop()

        start_rect = self.search_bar.geometry()
        if not self._animation_enabled or start_rect == target_rect:
            self.search_bar.setGeometry(target_rect)
            self._finish_transition(target_is_expanded)
            return

        self._anim.setStartValue(start_rect)
        self._anim.setEndValue(target_rect)
        self._anim_target = target_is_expanded
        self._anim.start()

    def _on_anim_finished(self):
        if self._anim_target is None:
            return
        target = self._anim_target
        self._anim_target = None
        self._finish_transition(target)

    def _finish_transition(self, target_is_expanded: bool):
        if target_is_expanded:
            # 展开完成，搜索栏保持显示
            pass
        else:
            # 关闭完成，隐藏搜索栏，恢复按钮
            if self.search_bar:
                self.search_bar.hide()
            self.image_button.show()
            self.more_button.show()
            self.search_placeholder.show()

    # ---------- 窗口缩放时动态适配动画终点 ----------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.action_widget:
            self.action_widget.setGeometry(
                0, self.action_widget.window_border_top_right_radius,
                self.width(), self.action_widget.height()
            )

        # 如果搜索栏展开且没有动画运行，直接跟随宽度变化
        if self.is_expanded and self.search_bar and self.search_bar.isVisible():
            if self._anim is None or self._anim.state() != QPropertyAnimation.Running:
                # 重新计算目标区域（宽度变了，高度不变）
                new_rect = QRect(
                    self.image_button.geometry().left(),
                    self.search_placeholder.geometry().top(),
                    self.more_button.geometry().right() - self.image_button.geometry().left(),
                    self.search_placeholder.height()
                )
                self.search_bar.setGeometry(new_rect)
            else:
                # 动画运行中，动态修正终点
                if self._anim_target is True:
                    new_rect = QRect(
                        self.image_button.geometry().left(),
                        self.search_placeholder.geometry().top(),
                        self.more_button.geometry().right() - self.image_button.geometry().left(),
                        self.search_placeholder.height()
                    )
                    self._anim.setEndValue(new_rect)

        elif not self.is_expanded and self._anim is not None and self._anim.state() == QPropertyAnimation.Running:
            if self._anim_target is False:
                # 关闭动画中窗口变化，更新目标为占位符最新位置
                new_target = self.search_placeholder.geometry()
                self._cached_placeholder_rect = new_target
                self._anim.setEndValue(new_target)

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

    # Quick test: create a virtual scrolling widget with inverted wheel direction.
    window = QWidget()
    window.setAttribute(Qt.WA_StyledBackground, True)
    layout_ = QVBoxLayout()
    t = TitleBar(window)
    layout_.addWidget(t)
    layout_.addStretch()
    window.setLayout(layout_)
    window.show()
    exit(app.exec())

