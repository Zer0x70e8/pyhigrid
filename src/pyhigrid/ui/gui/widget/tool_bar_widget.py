#
""""""

from typing_extensions import Callable

from PySide6.QtCore import Qt, Signal, QRect, QPropertyAnimation  # , QPoint
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton

# from ..anim.search_bar_anim import Anim
from pyhigrid.ui.gui.anim.search_bar_anim import Anim

class SearchBarLayoutPlaceholder(QWidget):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchPlaceholder")

        self.setAttribute(Qt.WA_StyledBackground, True)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SearchBar(QWidget):
    closed = Signal()

    def __init__(self, parent=None, placeholder: SearchBarLayoutPlaceholder = None):
        super().__init__(parent)
        self.placeholder = placeholder
        self.setObjectName("SearchBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("search...")
        self.line_edit.setObjectName("SearchLineEdit")

        self.close_btn: QPushButton = QPushButton("✕")
        self.close_btn.setObjectName("SearchCloseBtn")
        # 点击关闭按钮时只发出 closed 信号，由 ToolBar 统一处理
        self.close_btn.clicked.connect(self.closed.emit)

        layout.addWidget(self.line_edit)
        layout.addWidget(self.close_btn)


class ToolBar(QWidget):
    layout_squeezed = Signal(bool)
    extend_search_bar = Signal()
    folded_search_bar = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self._placeholder = None
        self._search_bar = None
        self.anim = None

        self.is_expanded = False
        self._updating_placeholder = False
        self._disable_amin = False

    @property
    def search_bar(self):
        return self._search_bar
    @search_bar.setter
    def search_bar(self, value: SearchBar):
        self._search_bar = value

    @property
    def placeholder(self):
        return self._placeholder
    @placeholder.setter
    def placeholder(
            self, value: SearchBarLayoutPlaceholder):
        self._placeholder = value

    @property
    def disable_amin(self):
        return self._disable_amin
    @disable_amin.setter
    def disable_amin(self, value: bool):
        self._disable_amin = value

    def expand_search(self):
        """（主动）展开搜索栏"""
        if self.is_expanded:
            return
        self.is_expanded = True

        #
        placeholder_rect = self.placeholder.geometry()
        # 目标几何：水平铺满，垂直跟随占位符（保持同一行、同样高度）
        target_rect = QRect(0, placeholder_rect.y(),
                            self.width(), placeholder_rect.height())

        # 懒创建搜索栏
        if self._search_bar is None:
            self._search_bar = SearchBar(
                parent=self,
                placeholder=self.placeholder
            )
            self._search_bar.closed.connect(self.collapse_search)

        # 设置搜索栏的起始几何为占位符位置，这样动画才能从该点开始
        self._search_bar.setGeometry(placeholder_rect)

        # 隐藏工具栏原有widget，显示搜索栏
        for w_ in self.children():
            if isinstance(w_, QWidget):
                if isinstance(w_, SearchBarLayoutPlaceholder):
                    continue
                if (hasattr(w_, "hide_handel") and
                        isinstance(w_.hide_handel, Callable)):
                    w_.hide_handel()
                else:
                    w_.hide()

        self.placeholder.hide()
        self._search_bar.show()
        self._search_bar.raise_()

        # 发射挤压信号（见注释：动画完全到达时不再重复，但逻辑上工具栏应立即视为被挤压）
        self.layout_squeezed.emit(True)

        # 启动过渡
        if not self._disable_amin:
            if self.anim is None:
                self.anim = Anim(self)
                self.anim.finished.connect(self._on_anim_finished)
            self.anim.start_expand(self.rect())

        else:
            # 动画禁用时直接定位
            self._search_bar.setGeometry(target_rect)

        self.extend_search_bar.emit()

    def collapse_search(self):
        """（主动）关闭搜索栏"""
        if not self.is_expanded:
            return
        self.is_expanded = False

        #
        gathering_position = self._query_placeholder_rect_safely()
        # if gathering_position.isNull():
        #       # 缓存占位符几何作为关闭目标
        #     gathering_position = self.placeholder.geometry()

        # gathering_position = QRect(
        #     QPoint(self.rect().width() // 2, self.rect().y()),
        #     QPoint(self.rect().width(), self.rect().height())
        # )

        # 启动关闭动画
        if not self._disable_amin:
            if self.anim is None:
                self.anim = Anim(self)
                self.anim.finished.connect(self._on_anim_finished)
            self.anim.start_collapse(gathering_position)

        else:
            # 动画禁用时直接定位并收尾
            if self._search_bar:
                self._search_bar.setGeometry(gathering_position)
            # self._finish_transition(False)

        self.folded_search_bar.emit()

    def _on_anim_finished(self):
        # 由 anim 内部的 _finish_transition 已经 emit layout_squeezed(False)，
        # 这里只处理控件显隐
        if not self.is_expanded and self._search_bar:
            self._search_bar.hide()
            # 恢复按钮
            for w_ in self.children():
                if isinstance(w_, QWidget) and not isinstance(w_, SearchBar):
                    w_: QWidget
                    if w_ is self.placeholder:
                        w_.show()
                    elif hasattr(w_, "hide_handel") and callable(w_.hide_handel):
                        # 如果原来有 show_handel 也可以调用，这里简单 show
                        w_.show()
                    else:
                        w_.show()

    def _query_placeholder_rect_safely(self):
        """
        瞬时布局查询法：临时显示占位符/按钮，强制布局后读取占位符的位置。
        使用防递归标志，避免触发新的 resizeEvent。
        """
        if self._updating_placeholder:
            return None

        self._updating_placeholder = True

        # 暂存当前可见性
        vis_map = {}
        for w_ in self.children():
            if isinstance(w_, QWidget):
                vis_map[w_] = w_.isVisible()

        placeholder_vis = self.placeholder.isVisible()
        search_vis = self.search_bar.isVisible() if self.search_bar else False

        # 临时显示占位符及按钮（如果它们原本隐藏）
        self.setUpdatesEnabled(False)
        for w_ in self.children():
            if isinstance(w_, QWidget):
                w_.show()
        self.placeholder.show()
        if self.search_bar:
            self.search_bar.hide()

        # 强制布局
        self.layout().activate()

        # 读取占位符几何
        rect = self.placeholder.geometry()

        # 恢复原先的可见性
        for w_, vis_ in vis_map.items():
            if isinstance(w_, QWidget):
                w_.setVisible(vis_)

        self.placeholder.setVisible(placeholder_vis)
        if self.search_bar:
            self.search_bar.setVisible(search_vis)

        self.setUpdatesEnabled(True)
        self.update()  # 触发一次重绘

        self._updating_placeholder = False
        return rect

    def resizeEvent(self, event):
        """窗口缩放时动态修正动画终点或直接更新几何"""
        super().resizeEvent(event)

        # 防递归：如果正在临时显示占位符以查询位置，不再处理 resize
        if self._updating_placeholder:
            return

        if self._disable_amin:
           return
        if self.anim is None:
            self.anim = Anim(self)
            self.anim.finished.connect(self._on_anim_finished)
        # 搜索栏完全展开且无动画 → 直接调整大小
        if self.is_expanded and self._search_bar and self._search_bar.isVisible():
            if self.anim.state() != QPropertyAnimation.Running:
                self._search_bar.setGeometry(self.rect())
            else:
                # 展开动画进行中 → 修正终点
                self.anim.update_target_rect(self.rect())

        # 如果是关闭动画进行中 → 修正关闭终点
        elif not self.is_expanded and self.anim.state() == QPropertyAnimation.Running:
            new_target = self._query_placeholder_rect_safely()
            if new_target is not None:
                self.anim.update_target_rect(new_target)


# ========== 简单测试 ==========
if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QVBoxLayout
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("搜索栏动画演示 - 统一过渡器")

    class ToolBar1(ToolBar):
        def __init__(self, parent):
            super().__init__(parent)

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
            layout.addStretch()
            layout.addWidget(self.placeholder)
            layout.addWidget(self.btn2)

            self.placeholder.clicked.connect(self.expand_search)

    toolbar = ToolBar1(window)
    toolbar.setFixedHeight(48)

    main_layout = QVBoxLayout(window)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(toolbar)
    main_layout.addStretch()

    # 样式表保持不变
    window.setStyleSheet("""
    #ToolBar {
        min-height: 56px;
        max-height: 56px;
        background-color: grey;
    }
    #ToolBtn {
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
    #ToolBtn:hover {
        background-color: #ddd;
    }
    #SearchPlaceholder {
        background-color: lightblue;
        min-width: 48px;
        max-width: 48px;
        min-height: 48px;
        max-height: 48px;
        border-radius: 4px;
        cursor: pointer;
    }
    #SearchPlaceholder:hover {
        background-color: #ccc;
    }
    #SearchBar {
        background-color: white;
        border-radius: 4px;
    }
    #SearchLineEdit {
        border: 1px solid #ccc;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 14px;
        background: white;
    }
    #SearchCloseBtn {
        min-width: 24px;
        max-width: 24px;
        min-height: 24px;
        max-height: 24px;
        border: none;
        background: transparent;
        font-size: 14px;
        color: #888;
    }
    #SearchCloseBtn:hover {
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
