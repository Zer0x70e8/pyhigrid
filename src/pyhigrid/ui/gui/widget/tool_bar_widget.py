"""
工具栏搜索栏 - 尺寸自适应 + 样式表驱动 + 统一几何过渡器
解决：动画打断、窗口缩放跟随、信号一致性、防递归查询等问题
"""
import sys
from PySide6.QtWidgets import (
    QWidget, QApplication, QHBoxLayout, QPushButton,
    QLineEdit, QVBoxLayout, QLabel, QPushButton
)
from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QMouseEvent


class SearchBarLayoutPlaceholder(QPushButton):
    """搜索栏占位按钮，点击呼出搜索栏"""
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("searchPlaceholder")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SearchBar(QWidget):
    """搜索栏控件，尺寸由外部在显示时动态赋予"""
    closed = Signal()

    def __init__(self, parent=None, placeholder: SearchBarLayoutPlaceholder = None):
        super().__init__(parent)
        self.placeholder = placeholder
        self.setObjectName("searchBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("搜索...")
        self.line_edit.setObjectName("searchLineEdit")

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("searchCloseBtn")
        # 点击关闭按钮时只发出 closed 信号，由 ToolBar 统一处理
        self.close_btn.clicked.connect(self.closed.emit)

        layout.addWidget(self.line_edit)
        layout.addWidget(self.close_btn)


class ToolBar(QWidget):
    """工具栏，支持搜索栏平滑展开动画（统一几何过渡器）"""

    # 布局挤压信号 – 含义：搜索栏已完全铺满工具栏（True）或已完全收回（False）
    layout_squeezed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toolBar")

        # ---------- 子控件 ----------
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.btn1 = QPushButton("←")
        self.btn2 = QPushButton("→")
        self.placeholder = SearchBarLayoutPlaceholder(self)

        for btn in (self.btn1, self.btn2):
            btn.setObjectName("toolBtn")

        layout.addWidget(self.btn1)
        layout.addWidget(self.placeholder)
        layout.addWidget(self.btn2)

        # ---------- 搜索栏状态 ----------
        self.search_bar = None          # 懒创建
        self.is_expanded = False        # 逻辑状态：True 表示搜索栏应当展开

        # ---------- 几何缓存 ----------
        self._cached_placeholder_rect = None   # 关闭动画的目标矩形

        # ---------- 动画系统（单一动画对象）----------
        self._transition_anim = QPropertyAnimation(self, b"geometry")  # 目标稍后设置
        self._transition_anim.setDuration(250)
        self._transition_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._transition_anim.finished.connect(self._on_transition_finished)
        self._anim_target_expanded = None  # 当前动画的收尾方向（True=展开，False=关闭）

        self._animation_enabled = True

        # ---------- 防递归标志 ----------
        self._updating_placeholder = False   # 正在临时显示以查询占位符位置

        # ---------- 信号连接 ----------
        self.placeholder.clicked.connect(self.expand_search)

    # ---------- 动画开关 ----------
    @property
    def animation_enabled(self) -> bool:
        return self._animation_enabled

    @animation_enabled.setter
    def animation_enabled(self, enabled: bool):
        self._animation_enabled = enabled

    # ============ 用户交互入口 ============
    def expand_search(self):
        """（主动）展开搜索栏"""
        if self.is_expanded:
            return
        self.is_expanded = True

        # 懒创建搜索栏
        if self.search_bar is None:
            self.search_bar = SearchBar(parent=self, placeholder=self.placeholder)
            self.search_bar.closed.connect(self.collapse_search)

        # 缓存占位符位置（此时占位符仍可见）
        self._cached_placeholder_rect = self.placeholder.geometry()

        # 隐藏工具栏原有按钮，显示搜索栏
        self.btn1.hide()
        self.btn2.hide()
        self.placeholder.hide()
        self.search_bar.show()
        self.search_bar.raise_()

        # 目标几何：铺满整个工具栏
        target_rect = self.rect()

        # 发射挤压信号（见注释：动画完全到达时不再重复，但逻辑上工具栏应立即视为被挤压）
        self.layout_squeezed.emit(True)

        # 启动过渡
        self._start_transition(target_rect, target_is_expanded=True)

    def collapse_search(self):
        """（主动）关闭搜索栏"""
        if not self.is_expanded:
            return
        self.is_expanded = False

        # 如果没有缓存（极少情况，例如从未展开就被强制关闭），用当前占位符几何兜底
        if self._cached_placeholder_rect is None:
            self._cached_placeholder_rect = self.placeholder.geometry()

        self._start_transition(self._cached_placeholder_rect, target_is_expanded=False)

    # ============ 统一几何过渡器 ============
    def _start_transition(self, target_rect: QRect, target_is_expanded: bool):
        """启动一次几何过渡（自动处理打断、禁用、直接完成）"""
        # 1. 停止正在运行的动画
        if self._transition_anim.state() == QPropertyAnimation.Running:
            self._transition_anim.stop()

        # 2. 起点：搜索栏当前的实际几何（即便动画中断在半路）
        start_rect = self.search_bar.geometry()

        # 3. 特殊情况：动画禁用 或 起点等于终点
        if not self._animation_enabled or start_rect == target_rect:
            # 直接跳到目标位置并收尾
            self.search_bar.setGeometry(target_rect)
            self._finish_transition(target_is_expanded)
            return

        # 4. 设置动画目标
        # 注意：动画目标对象应始终为 self.search_bar
        self._transition_anim.setTargetObject(self.search_bar)
        self._transition_anim.setStartValue(start_rect)
        self._transition_anim.setEndValue(target_rect)
        self._anim_target_expanded = target_is_expanded

        # 5. 启动
        self._transition_anim.start()

    def _on_transition_finished(self):
        """动画正常结束时的收尾"""
        # 防止重复收尾（例如手动调用了 stop 又收到 finished？Qt 不会，但安全起见）
        if self._anim_target_expanded is None:
            return
        target = self._anim_target_expanded
        self._anim_target_expanded = None
        self._finish_transition(target)

    def _finish_transition(self, target_is_expanded: bool):
        """统一的收尾动作：根据动画目标方向调整控件可见性和信号"""
        if target_is_expanded:
            # 展开完成：搜索栏已正确铺满，无需额外操作
            # 注意：layout_squeezed(True) 已在 expand_search 中提前发射
            pass
        else:
            # 关闭完成：隐藏搜索栏，恢复按钮
            if self.search_bar:
                self.search_bar.hide()
            self.btn1.show()
            self.btn2.show()
            self.placeholder.show()
            # 发射关闭完成信号
            self.layout_squeezed.emit(False)

    # ============ 窗口大小变化处理 ============
    def resizeEvent(self, event):
        """窗口缩放时动态修正动画终点或直接更新几何"""
        super().resizeEvent(event)

        # 防递归：如果正在临时显示占位符以查询位置，不再处理 resize
        if self._updating_placeholder:
            return

        # 情况1：搜索栏完全展开（逻辑状态为True），没有动画运行 → 直接跟随
        if self.is_expanded and self.search_bar and self.search_bar.isVisible():
            if self._transition_anim.state() != QPropertyAnimation.Running:
                self.search_bar.setGeometry(self.rect())
            else:
                # 情况2：展开动画正在运行 → 动态修正终点
                if self._anim_target_expanded is True:
                    self._transition_anim.setEndValue(self.rect())

        # 情况3：逻辑上处于关闭状态，但关闭动画正在运行 → 动态修正关闭终点
        elif not self.is_expanded and self._transition_anim.state() == QPropertyAnimation.Running:
            if self._anim_target_expanded is False:
                new_target = self._query_placeholder_rect_safely()
                if new_target is not None:
                    self._cached_placeholder_rect = new_target
                    self._transition_anim.setEndValue(new_target)

    def _query_placeholder_rect_safely(self):
        """
        瞬时布局查询法：临时显示占位符/按钮，强制布局后读取占位符的位置。
        使用防递归标志，避免触发新的 resizeEvent。
        """
        if self._updating_placeholder:
            return None

        self._updating_placeholder = True

        # 暂存当前可见性
        btn1_vis = self.btn1.isVisible()
        btn2_vis = self.btn2.isVisible()
        placeholder_vis = self.placeholder.isVisible()
        search_vis = self.search_bar.isVisible() if self.search_bar else False

        # 临时显示占位符及按钮（如果它们原本隐藏）
        self.setUpdatesEnabled(False)
        self.btn1.show()
        self.btn2.show()
        self.placeholder.show()
        if self.search_bar:
            self.search_bar.hide()

        # 强制布局
        self.layout().activate()

        # 读取占位符几何
        rect = self.placeholder.geometry()

        # 恢复原先的可见性
        self.btn1.setVisible(btn1_vis)
        self.btn2.setVisible(btn2_vis)
        self.placeholder.setVisible(placeholder_vis)
        if self.search_bar:
            self.search_bar.setVisible(search_vis)

        self.setUpdatesEnabled(True)
        self.update()  # 触发一次重绘

        self._updating_placeholder = False
        return rect


# ========== 简单测试 ==========
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("搜索栏动画演示 - 统一过渡器")

    toolbar = ToolBar(window)

    main_layout = QVBoxLayout(window)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(toolbar)
    main_layout.addStretch()

    # 样式表保持不变
    window.setStyleSheet("""
    #toolBar {
        min-height: 56px;
        max-height: 56px;
        background-color: grey;
    }
    #toolBtn {
        background-color: lightgrey;
        min-width: 48px;
        max-width: 48px;
        min-height: 48px;
        max-height: 48px;
        border: none;
        border-radius: 4px;
        font-size: 16px;
        color: #333;
    }
    #toolBtn:hover {
        background-color: #ddd;
    }
    #searchPlaceholder {
        background-color: lightblue;
        min-width: 48px;
        max-width: 48px;
        min-height: 48px;
        max-height: 48px;
        border-radius: 4px;
        cursor: pointer;
    }
    #searchPlaceholder:hover {
        background-color: #ccc;
    }
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
        min-width: 24px;
        max-width: 24px;
        min-height: 24px;
        max-height: 24px;
        border: none;
        background: transparent;
        font-size: 14px;
        color: #888;
    }
    #searchCloseBtn:hover {
        color: #333;
        background-color: #eee;
        border-radius: 4px;
    }
    """)

    # 可测试动画开关
    # toolbar.animation_enabled = False

    window.resize(400, 80)
    window.show()
    sys.exit(app.exec())

