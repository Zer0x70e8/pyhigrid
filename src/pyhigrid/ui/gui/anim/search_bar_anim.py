#
""""""

from typing import TYPE_CHECKING

from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QRect

if TYPE_CHECKING:
    # noinspection PyUnusedImports
    from ..widget.tool_bar_widget import ToolBar

class Anim(QPropertyAnimation):
    """
    统一几何过渡器，专用于搜索栏的展开/折叠动画。
    接管动画目标、打断、方向记录，并提供缩放跟随接口。
    """
    def __init__(self, parent: "ToolBar" = None):
        super().__init__(parent)
        self._toolbar = parent
        self._enabled = True

        # 使用一个 QPropertyAnimation 实例，目标稍后设置
        self.setTargetObject(None)  # type: ignore[arg-type]
        self.setDuration(250)
        self.setEasingCurve(QEasingCurve.OutCubic)
        self.finished.connect(self._on_finished)

        # 当前动画的收尾方向
        self._target_expanded = None   # True: 展开, False: 关闭, None: 无动画

    # ---------- 开关 ----------
    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    # ---------- 公开接口 ----------
    def start_expand(self, target_rect: QRect):
        """启动展开动画，目标矩形为 target_rect"""
        self._start_transition(target_rect, True)

    def start_collapse(self, target_rect: QRect):
        """启动关闭动画，目标矩形为 target_rect"""
        self._start_transition(target_rect, False)

    def update_target_rect(self, rect: QRect):
        """
        缩放时动态修正正在运行的动画的终点。
        仅在动画方向匹配时生效。
        """
        if self.state() == QPropertyAnimation.Running and self._target_expanded is not None:
            # 当前动画方向与所属过渡匹配时才修正终点
            if self._toolbar and self._toolbar.search_bar:
                self.setEndValue(rect)

    # ---------- 内部过渡控制 ----------
    def _start_transition(self, target_rect: QRect, is_expanded: bool):
        """统一的过渡启动入口（处理打断、直接完成）"""
        toolbar = self._toolbar
        if not toolbar or not toolbar.search_bar:
            return

        search_bar = toolbar.search_bar

        # 1. 停止正在运行的动画
        if self.state() == QPropertyAnimation.Running:
            self.stop()

        # 2. 起点：搜索栏当前的实际几何
        start_rect = search_bar.geometry()

        # 3. 动画禁用 或 起点等于终点 → 直接完成
        if not self._enabled or start_rect == target_rect:
            search_bar.setGeometry(target_rect)
            self._finish_transition(is_expanded)
            return

        # 4. 设置动画
        self.setTargetObject(search_bar)
        self.setPropertyName(b"geometry")
        self.setStartValue(start_rect)
        self.setEndValue(target_rect)
        self._target_expanded = is_expanded

        # 5. 发射
        self.start()

    def _on_finished(self):
        """动画正常结束时的收尾"""
        if self._target_expanded is None:
            return
        target = self._target_expanded
        self._target_expanded = None
        self._finish_transition(target)

    def _finish_transition(self, is_expanded: bool):
        """动画完成后的清理与信号发射"""
        toolbar = self._toolbar
        if not toolbar:
            return

        if is_expanded:
            # 展开完成：逻辑已提前处理，这里可留空
            # 但为了防止信号丢失，可以补发 layout_squeezed(True)
            # 但按照现有设计，True 已在 expand_search 中提前发射
            pass
        else:
            # 关闭完成：由 Toolbar 负责恢复按钮可见性并发射信号
            toolbar.layout_squeezed.emit(False)
