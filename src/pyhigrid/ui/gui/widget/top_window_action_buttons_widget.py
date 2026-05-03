#
"""top window action buttons widget"""

from PySide6.QtWidgets import QWidget, QHBoxLayout

from .action_buttons import CloseButton, MaximizeButton, MinimizeButton

from ..utils.window_corner_radius import get_system_window_corner_radius
from ..utils.qss_border_radius_getter import extract_border_radius


class TopWindowActionButtonsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.sys_window_radius = get_system_window_corner_radius()
        self.window_border_top_left_radius = int(self.sys_window_radius)
        self.window_border_top_right_radius = int(self.sys_window_radius)

        self._action_btn_on_left: bool | None = False  # 为空时隐藏它

        self._first_refresh = False

        self.left_placeholder = QWidget(self)
        self.right_placeholder = QWidget(self)

        self.close_button = CloseButton(self)
        self.maximize_button = MaximizeButton(self)
        self.minimize_button = MinimizeButton(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.setLayout(layout)

        # layout.addWidget(self.left_placeholder)
        # layout.addWidget(self.close_button)
        # layout.addWidget(self.maximize_button)
        # layout.addWidget(self.minimize_button)
        # layout.addStretch()
        # layout.addWidget(self.right_placeholder)

        self.setup_()

    def setup_(self):
        self.left_placeholder.setFixedWidth(
            int(self.window_border_top_left_radius)
        )
        self.right_placeholder.setFixedWidth(
            int(self.window_border_top_right_radius)
        )

        self.setMaximumHeight(
            int(self.window_border_top_left_radius * 2)
        )

        self._update_placeholder_widths()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._first_refresh:
            radius_info = extract_border_radius(
                self.window().styleSheet(),
                self.window().objectName(),
                match_mode="base"
            )
            border_radius = radius_info.get("border_radius", self.sys_window_radius)
            self.window_border_top_left_radius = radius_info.get("top_left_radius", border_radius)
            self.window_border_top_right_radius = radius_info.get("top_right_radius", border_radius)
            self._first_refresh = True
        # 每次显示都按当前设定刷新布局，保证初始状态正确
        self._apply_layout()

    def set_act_btn_position(self, pos: str | bool | None = ""):
        if pos == "":
            return
        # 记录旧值，避免重复操作
        old_pos = self._action_btn_on_left
        match pos:
            case False | "right":
                self._action_btn_on_left = False
            case True | "left":
                self._action_btn_on_left = True
            case None | "none" | "disabled":
                self._action_btn_on_left = None
        # 只有位置真正变化时才刷新布局
        if self._action_btn_on_left != old_pos:
            self._apply_layout()

    def _apply_layout(self):
        """根据 _action_btn_on_left 的值重建水平布局"""
        layout: QHBoxLayout = self.layout()  # noqa
        # 移除布局中所有项，弹簧直接删除，控件保留下来
        while layout.count():
            item = layout.takeAt(0)
            # 如果是弹簧(QSpacerItem)，需要手动销毁，否则内存泄漏
            if item.spacerItem():
                # PySide6 中直接删除 Python 对象即可触发 C++ 析构
                del item
            # 如果是控件，不做额外处理，让控件本身继续存活
            # （之后会重新 addWidget）
        # 控制按钮可见性
        if self._action_btn_on_left is None:
            self.close_button.hide()
            self.maximize_button.hide()
            self.minimize_button.hide()
            # 隐藏时只保留占位符，高度置0
            layout.addWidget(self.left_placeholder)
            layout.addWidget(self.right_placeholder)
            self.setFixedHeight(0)
        elif self._action_btn_on_left:  # 按钮在左侧（如 macOS 风格）
            self.close_button.show()
            self.maximize_button.show()
            self.minimize_button.show()
            layout.addWidget(self.left_placeholder)
            layout.addWidget(self.close_button)
            layout.addWidget(self.maximize_button)
            layout.addWidget(self.minimize_button)
            layout.addStretch()
            layout.addWidget(self.right_placeholder)
        else:  # 按钮在右侧（如 Windows 风格，顺序为 最小化、最大化、关闭）
            self.close_button.show()
            self.maximize_button.show()
            self.minimize_button.show()
            layout.addWidget(self.left_placeholder)
            layout.addStretch()
            layout.addWidget(self.minimize_button)
            layout.addWidget(self.maximize_button)
            layout.addWidget(self.close_button)
            layout.addWidget(self.right_placeholder)

        # 根据当前位置调整占位符宽度和最大高度
        self._update_placeholder_widths()

    def _update_placeholder_widths(self):
        """设置左右占位符的宽度，以及控件自身的最大高度"""
        if self._action_btn_on_left is False:  # 按钮在右侧
            left_w = 0
            right_w = int(self.window_border_top_right_radius)
            max_h = int(self.window_border_top_right_radius * 2)
        elif self._action_btn_on_left:  # 按钮在左侧
            left_w = int(self.window_border_top_left_radius)
            right_w = 0
            max_h = int(self.window_border_top_left_radius * 2)
        else:  # 隐藏按钮
            left_w = 0
            right_w = 0
            max_h = 0

        self.left_placeholder.setFixedWidth(left_w)
        self.right_placeholder.setFixedWidth(right_w)
        # 高度设置保持不变
        if self._action_btn_on_left is not None:
            self.setMaximumHeight(max_h)
            self.setMinimumHeight(0)
            self.setFixedHeight(16777215)
        else:
            self.setFixedHeight(0)

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QVBoxLayout

    app = QApplication(sys.argv)

    window = QWidget()
    widget = TopWindowActionButtonsWidget(window)

    layout_ = QVBoxLayout(window)
    layout_.addWidget(widget)
    window.setLayout(layout_)

    window.show()

    exit(app.exec())
