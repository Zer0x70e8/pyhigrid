#
""""""

import sys
from PySide6.QtCore import (
    Qt, QPoint, QRect, QPropertyAnimation,
    QEasingCurve, QParallelAnimationGroup, QAbstractAnimation
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QScrollArea,
    QHBoxLayout, QPushButton, QFrame, QLabel
)


class AlbumTabBar(QWidget):
    """iOS 照片风格的可滚动标签栏，带平滑指示条动画"""

    def __init__(self, tabs, parent=None):
        super().__init__(parent)
        # 固定总高度，为指示条留出空间
        self.setFixedHeight(48)

        # ---------- 滚动区域 ----------
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        # 只允许水平滚动，隐藏滚动条
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        # ---------- 内容容器 ----------
        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 0, 16, 0)  # 左右边距，避免首尾按钮贴边
        self.content_layout.setSpacing(8)
        self.content_layout.setAlignment(Qt.AlignVCenter)      # 按钮垂直居中

        self.scroll_area.setWidget(self.content_widget)

        # ---------- 选中指示条 ----------
        self.indicator = QFrame(self)
        self.indicator.setFixedHeight(3)
        # 使用系统强调色并添加圆角，自动适配深色模式
        self.indicator.setStyleSheet(
            "background-color: palette(highlight); border-radius: 2px; border: none;"
        )
        self.indicator.show()

        # ---------- 创建按钮 ----------
        self.buttons = []
        for i, text in enumerate(tabs):
            btn = QPushButton(text)
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)                     # 去除焦点虚线框
            btn.clicked.connect(lambda checked, idx=i: self.on_button_clicked(idx))
            self.buttons.append(btn)
            self.content_layout.addWidget(btn)

        # 初始选中第一个
        self.current_index = 0
        self.update_button_styles()

        # 用于并行动画
        self.anim_group = QParallelAnimationGroup()

    # ==================== 事件处理 ====================

    def showEvent(self, event):
        """首次显示后，确保指示条定位准确"""
        super().showEvent(event)
        self.update_indicator_position(animated=False)

    def resizeEvent(self, event):
        """窗口大小变化时，立即更新指示条位置并停止动画"""
        super().resizeEvent(event)
        if self.anim_group.state() == QAbstractAnimation.Running:
            self.anim_group.stop()
        self.update_indicator_position(animated=False)

    def changeEvent(self, event):
        """系统主题（亮/暗）切换时，刷新按钮文字颜色"""
        if event.type() == event.Type.PaletteChange:
            self.update_button_styles()
            # 强制刷新指示条样式（虽然 palette(highlight) 通常自动更新）
            self.indicator.style().unpolish(self.indicator)
            self.indicator.style().polish(self.indicator)
        super().changeEvent(event)

    # ==================== 样式与布局 ====================

    def update_button_styles(self):
        """根据选中状态设置按钮样式，颜色由系统调色板决定"""
        for i, btn in enumerate(self.buttons):
            if i == self.current_index:
                # 选中：加粗 + 主文字色（亮色模式黑，暗色模式白）
                btn.setStyleSheet("""
                    QPushButton {
                        color: palette(window-text);
                        font-weight: bold;
                        padding: 6px 16px;
                        border: none;
                        background: transparent;
                    }
                """)
            else:
                # 未选中：常规字重 + 次要文字色
                btn.setStyleSheet("""
                    QPushButton {
                        color: palette(mid);
                        font-weight: normal;
                        padding: 6px 16px;
                        border: none;
                        background: transparent;
                    }
                """)
        # 通知布局更新按钮尺寸（加粗后宽度可能变化）
        self.content_layout.activate()

    def calculate_indicator_geometry(self, index):
        """计算指定按钮下方指示条的目标矩形（相对于本控件）"""
        button = self.buttons[index]
        pos = button.mapTo(self, QPoint(0, 0))
        x = pos.x()
        y = pos.y() + button.height() + 2   # 按钮底部留 2px 间距
        w = button.width()
        h = self.indicator.height()
        return QRect(x, y, w, h)

    def update_indicator_position(self, animated=True, index=None):
        """更新指示条位置，可选动画过渡"""
        if index is None:
            index = self.current_index
        target_rect = self.calculate_indicator_geometry(index)
        if not animated:
            self.indicator.setGeometry(target_rect)
        else:
            self.animate_indicator(target_rect, index)

    # ==================== 动画 ====================

    def animate_indicator(self, target_rect, index):
        """同时执行指示条滑动和滚动区域居中动画"""
        # 停止正在进行的动画
        if self.anim_group.state() == QAbstractAnimation.Running:
            self.anim_group.stop()

        # 1. 指示条几何动画（位置 + 宽度）
        start_geom = self.indicator.geometry()
        anim = QPropertyAnimation(self.indicator, b"geometry")
        anim.setDuration(300)
        anim.setStartValue(start_geom)
        anim.setEndValue(target_rect)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        # 2. 滚动动画：让选中的按钮水平居中
        button = self.buttons[index]
        btn_viewport_pos = button.mapTo(self.scroll_area.viewport(), QPoint(0, 0))
        btn_w = button.width()
        viewport_w = self.scroll_area.viewport().width()
        scroll_bar = self.scroll_area.horizontalScrollBar()

        target_scroll = btn_viewport_pos.x() + btn_w / 2 - viewport_w / 2
        target_scroll = max(0, min(target_scroll, scroll_bar.maximum()))

        scroll_anim = QPropertyAnimation(scroll_bar, b"value")
        scroll_anim.setDuration(300)
        scroll_anim.setStartValue(scroll_bar.value())
        scroll_anim.setEndValue(target_scroll)
        scroll_anim.setEasingCurve(QEasingCurve.OutCubic)

        # 并行播放
        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(anim)
        self.anim_group.addAnimation(scroll_anim)
        self.anim_group.start()

    # ==================== 交互 ====================

    def on_button_clicked(self, index):
        """点击标签时触发过渡动画"""
        if index == self.current_index:
            return

        # 保存指示条当前位置作为动画起点（此时还是旧按钮的几何）
        old_geometry = self.indicator.geometry()

        # 更新选中状态和样式（旧按钮取消加粗，新按钮加粗）
        self.current_index = index
        self.update_button_styles()

        # 强制布局立即生效，以便获得新按钮的准确宽度
        self.content_layout.activate()

        # 计算目标几何（新按钮加粗后的位置与宽度）
        target_rect = self.calculate_indicator_geometry(index)

        # 将指示条先还原到旧位置，动画将从这里平滑过渡到新位置
        self.indicator.setGeometry(old_geometry)
        self.animate_indicator(target_rect, index)


# ==================== 演示窗口 ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 使用 Fusion 风格，在各平台上表现统一
    app.setStyle("Fusion")

    window = QWidget()
    window.setWindowTitle("iOS 风格相簿标签栏")
    layout = QVBoxLayout(window)

    # 示例标签
    tabs = ["Years", "Months", "Days", "All Photos"]
    tab_bar = AlbumTabBar(tabs)
    layout.addWidget(tab_bar)

    # 下方占位内容
    layout.addWidget(QLabel("照片内容区域"), alignment=Qt.AlignCenter)
    layout.addStretch()

    window.resize(520, 250)
    window.show()

    sys.exit(app.exec())
