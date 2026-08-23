#
"""top window action buttons widgets"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QSizePolicy,
)

from .action_buttons import CloseButton, MaximizeButton, MinimizeButton
from ..utils.window_corner_radius import get_system_window_corner_radius
# from ..utils.qss_border_radius_getter import extract_border_radius


class TopWindowActionButtonsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.sys_window_radius = get_system_window_corner_radius()
        # 确保初始值合理（不为0）
        if self.sys_window_radius <= 0:
            self.sys_window_radius = 10  # 一个安全的默认圆角值

        self.window_border_top_left_radius = int(self.sys_window_radius)
        self.window_border_top_right_radius = int(self.sys_window_radius)

        self._action_btn_on_left: bool | None = False
        # self._first_refresh = False

        self.left_placeholder = QWidget(self)
        self.right_placeholder = QWidget(self)

        self.close_button = CloseButton(self)
        self.maximize_button = MaximizeButton(self)
        self.minimize_button = MinimizeButton(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.setLayout(layout)

        self.setup_()

    def setup_(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName(type(self).__name__)

        # 初始占位宽度使用当前存储的圆角值
        self._update_placeholder_widths()

        # 设置垂直方向策略为 Preferred，这样它可以根据内容获得合理高度，
        # 同时最大高度由 _update_placeholder_widths 中的 setMaximumHeight 限制
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def showEvent(self, event):
        super().showEvent(event)
        # if not self._first_refresh:
        #     # 只有首次显示时才尝试从样式表读取圆角
        #     radius_info = extract_border_radius(
        #         self.window().styleSheet(),
        #         self.window().objectName(),
        #         match_mode="base"
        #     )
        #     # 若提取成功且值大于0才更新，否则保留系统圆角
        #     if radius_info:
        #         border_radius = radius_info.get("border_radius", 0)
        #         if border_radius > 0:
        #             self.window_border_top_left_radius = int(
        #                 radius_info.get("top_left_radius", border_radius)
        #             )
        #             self.window_border_top_right_radius = int(
        #                 radius_info.get("top_right_radius", border_radius)
        #             )
        #     self._first_refresh = True

        # 每次显示都重新应用布局，保证状态正确
        self._apply_layout()

    def set_act_btn_position(self, pos: str | bool | None = ""):
        if pos == "":
            return
        old_pos = self._action_btn_on_left
        match pos:
            case False | "right":
                self._action_btn_on_left = False
            case True | "left":
                self._action_btn_on_left = True
            case None | "none" | "disabled":
                self._action_btn_on_left = None

        if self._action_btn_on_left != old_pos:
            self._apply_layout()

    def _apply_layout(self):
        """根据 _action_btn_on_left 的值重建水平布局"""
        layout: QHBoxLayout = self.layout()
        # 清空布局中的所有项，弹簧直接删除，控件保留
        while layout.count():
            item = layout.takeAt(0)
            if item.spacerItem():
                del item  # 删除弹簧对象，释放内存

        # 控制按钮可见性
        if self._action_btn_on_left is None:
            self.close_button.hide()
            self.maximize_button.hide()
            self.minimize_button.hide()
            # 只保留占位符
            layout.addWidget(self.left_placeholder)
            layout.addWidget(self.right_placeholder)
        elif self._action_btn_on_left:  # 按钮在左（macOS 风格）
            self.close_button.show()
            self.maximize_button.show()
            self.minimize_button.show()
            layout.addWidget(self.left_placeholder)
            layout.addWidget(self.close_button)
            layout.addWidget(self.maximize_button)
            layout.addWidget(self.minimize_button)
            layout.addStretch()
            layout.addWidget(self.right_placeholder)
        else:  # 按钮在右（Windows 风格）
            self.close_button.show()
            self.maximize_button.show()
            self.minimize_button.show()
            layout.addWidget(self.left_placeholder)
            layout.addStretch()
            layout.addWidget(self.minimize_button)
            layout.addWidget(self.maximize_button)
            layout.addWidget(self.close_button)
            layout.addWidget(self.right_placeholder)

        # 根据当前状态更新占位宽度和高度限制
        self._update_placeholder_widths()

    def _update_placeholder_widths(self):
        """设置左右占位符的宽度，以及控件自身的最大高度（保证按钮不被圆角遮挡）"""
        if self._action_btn_on_left is False:  # 右侧按钮
            left_w = 0
            right_w = int(self.window_border_top_right_radius)
            max_h = int(self.window_border_top_right_radius * 2)
        elif self._action_btn_on_left:  # 左侧按钮
            left_w = int(self.window_border_top_left_radius)
            right_w = 0
            max_h = int(self.window_border_top_left_radius * 2)
        else:  # 隐藏状态
            left_w = 0
            right_w = 0
            max_h = 0

        self.left_placeholder.setFixedWidth(left_w)
        self.right_placeholder.setFixedWidth(right_w)

        # 按钮隐藏时直接将控件高度降为0
        if self._action_btn_on_left is None:
            self.setMinimumHeight(0)
            self.setMaximumHeight(0)
            self.setFixedHeight(0)  # 彻底隐藏
        else:
            # 按钮可见时，限制最大高度，但允许布局自然伸缩
            # 设置最小高度为0，确保不会被强制撑大
            self.setMinimumHeight(0)
            # 保证至少有一个最小可见高度（例如按钮高度30），避免圆角为0时控件消失
            if max_h <= 0:
                max_h = 30  # 按钮常见高度
            self.setMaximumHeight(max_h)
            # 移除之前错误的 setFixedHeight(16777215)，改用 setSizePolicy 保证伸缩
            # 这里通过设置 Preferred 垂直策略，使控件占用其 sizeHint 提供的高度，
            # 同时受上面 setMaximumHeight 的限制。
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QVBoxLayout

    app = QApplication(sys.argv)

    window = QWidget()
    window.resize(400, 300)
    widget = TopWindowActionButtonsWidget(window)

    # 测试：可以在这里调用 set_act_btn_position 切换位置
    # widgets.set_act_btn_position("left")

    layout_ = QVBoxLayout(window)
    layout_.setContentsMargins(0, 0, 0, 0)
    layout_.addWidget(widget)
    layout_.addStretch()  # 让按钮条在上方，其余空间留给空白
    window.setLayout(layout_)

    window.show()
    sys.exit(app.exec())
