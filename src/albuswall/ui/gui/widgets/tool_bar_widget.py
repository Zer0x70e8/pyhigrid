#
""""""

from typing import Optional

from PySide6.QtCore import Qt, Signal, QRect, QPropertyAnimation
from PySide6.QtStateMachine import QStateMachine
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLineEdit,
                               QPushButton, QFrame, QComboBox
                               )

try:
    from ..anims.search_bar_anim import Anim
except ImportError:
    from albuswall.ui.gui.anims.search_bar_anim import Anim


class SearchBarLayoutPlaceholder(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchPlaceholder")

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


class SearchBar(QFrame):
    closed = Signal()
    search = Signal(dict)

    def __init__(self,
                 parent=None,
                 placeholder: Optional[SearchBarLayoutPlaceholder] = None
                 ):
        super().__init__(parent)
        self.placeholder = placeholder
        self.setObjectName("SearchBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(0)

        self.line_edit: QLineEdit = QLineEdit()
        self.line_edit.setPlaceholderText(self.tr("search..."))
        self.line_edit.setObjectName("SearchLineEdit")

        self.option_combo = QComboBox()
        self.option_combo.setObjectName("SearchOptionCombo")
        if __debug__:
            self.option_combo.addItems(["all", "test1", "test2"])

        self.search_btn: QPushButton = QPushButton("🔍")
        self.search_btn.setObjectName("SearchSearchBtn")

        self.close_btn: QPushButton = QPushButton("✕")
        self.close_btn.setObjectName("SearchCloseBtn")
        # 点击关闭按钮时只发出 closed 信号，由 ToolBar 统一处理
        self.close_btn.clicked.connect(self.closed.emit)

        layout.addWidget(self.line_edit)
        layout.addWidget(self.option_combo)
        layout.addWidget(self.search_btn)
        layout.addWidget(self.close_btn)

        self.line_edit.returnPressed.connect(self._trigger_search)
        self.search_btn.clicked.connect(self._trigger_search)

    def _trigger_search(self):
        data = {
            "text": self.line_edit.text().strip(),
            "option": self.option_combo.currentData(),  # or currentText()
        }
        self.search.emit(data)


class ToolBarStateMachine(QStateMachine):
    """
    负责管理工具栏子控件的隐藏/显示状态，
    以及提供安全的占位符几何查询。
    """
    def __init__(self, target: 'ToolBar', parent=None):
        super().__init__(parent)
        self.target: 'ToolBar' = target
        self._vis_map = {}          # 记录子控件原始可见性
        self._updating_placeholder = False

    @property
    def updating_placeholder(self):
        return self._updating_placeholder

    def hide_children(self):
        """隐藏工具栏原有 widget，显示搜索栏"""
        self._vis_map = {}
        for w in self.target.children():
            if not isinstance(w, QWidget):
                continue
            self._vis_map[w] = w.isVisible()

            if isinstance(w, SearchBarLayoutPlaceholder):
                continue

            if hasattr(w, "hide_handel") and callable(w.hide_handel):
                w.hide_handel()
            else:
                w.hide()

    def show_children(self, force=False):
        """恢复子控件的可见性"""
        if not force:
            for w, vis in self._vis_map.items():
                if isinstance(w, QWidget):
                    w.setVisible(vis)
            return

        for w in self.target.children():
            if isinstance(w, QWidget) and not isinstance(w, SearchBar):
                w: QWidget
                if w is self.target.placeholder:
                    w.show()
                elif hasattr(w, "hide_handel") and callable(w.hide_handel):
                    w.show()
                else:
                    w.show()

    def query_placeholder_rect_safely(self) -> Optional[QRect]:
        """
        瞬时布局查询法：临时显示占位符/按钮，强制布局后读取占位符的位置。
        使用防递归标志，避免触发新的 resizeEvent。
        """
        if self._updating_placeholder:
            return None

        self._updating_placeholder = True
        target = self.target

        # 暂存当前可见性
        vis_map = {}
        for w in target.children():
            if isinstance(w, QWidget):
                vis_map[w] = w.isVisible()

        placeholder_vis = target.placeholder.isVisible()
        search_vis = target.search_bar.isVisible() if target.search_bar else False

        # 临时显示占位符及按钮（如果它们原本隐藏）
        target.setUpdatesEnabled(False)
        for w in target.children():
            if isinstance(w, QWidget):
                w.show()
        target.placeholder.show()
        if target.search_bar:
            target.search_bar.hide()

        # 强制布局
        if target.layout() is not None:
            target.layout().activate()  # type: ignore

        # 读取占位符几何
        rect = target.placeholder.geometry()

        # 恢复原先的可见性
        for w, vis in vis_map.items():
            if isinstance(w, QWidget):
                w.setVisible(vis)

        target.placeholder.setVisible(placeholder_vis)
        if target.search_bar:
            target.search_bar.setVisible(search_vis)

        target.setUpdatesEnabled(True)
        target.update()

        self._updating_placeholder = False
        return rect


# noinspection SpellCheckingInspection
class ToolBar(QWidget):
    layout_squeezed = Signal(bool)
    extend_search_bar = Signal()
    folded_search_bar = Signal()
    search = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._placeholder = None
        self._search_bar = None
        self.anim: Optional[Anim] = None
        self.state_machine = ToolBarStateMachine(self)

        self.is_expanded = False
        self.disable_anim = False

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
    def placeholder(self, value: SearchBarLayoutPlaceholder):
        self._placeholder = value

    def expand_search(self):
        """展开搜索栏"""
        if self.is_expanded:
            return
        self.is_expanded = True

        placeholder_rect = self.placeholder.geometry()
        target_rect = QRect(0, placeholder_rect.y(),
                            self.width(), placeholder_rect.height())

        self.ensure_search_bar()

        # 设置搜索栏的起始几何为占位符位置
        self._search_bar.setGeometry(placeholder_rect)

        # 隐藏子控件（由状态机管理）
        self.state_machine.hide_children()

        self.placeholder.hide()
        self._search_bar.show()
        self._search_bar.raise_()

        self.layout_squeezed.emit(True)

        if not self.disable_anim:
            self.ensure_anim()
            assert self.anim
            self.anim.start_expand(self.rect())
        else:
            self._search_bar.setGeometry(target_rect)

        self.extend_search_bar.emit()

    def collapse_search(self):
        """关闭搜索栏"""
        if not self.is_expanded:
            return
        self.is_expanded = False

        gathering_position = self.state_machine.query_placeholder_rect_safely()

        self.layout_squeezed.emit(False)

        if gathering_position is None:
            if self._search_bar:
                self._search_bar.setGeometry(0, 0, 0, 0)
        elif not self.disable_anim:
            self.ensure_anim()
            assert self.anim
            self.anim.start_collapse(gathering_position)
        else:
            if self._search_bar:
                self._search_bar.setGeometry(gathering_position)

        self.folded_search_bar.emit()

    def ensure_anim(self):
        if self.anim is None:
            self.anim = Anim(self)
            assert self.anim
            self.anim.finished.connect(self._on_anim_finished)

    def ensure_search_bar(self):
        """懒创建搜索栏"""
        if self._search_bar is None:
            self._search_bar = SearchBar(
                parent=self,
                placeholder=self.placeholder
            )
            self._search_bar.closed.connect(self.collapse_search)

    def _on_anim_finished(self):
        """动画完成后的收尾工作（隐藏管理由状态机完成）"""
        if not self.is_expanded and self._search_bar:
            self._search_bar.hide()
            self.state_machine.show_children()

    def resizeEvent(self, event):
        """窗口缩放时动态修正动画终点或直接更新几何"""
        if (self.state_machine.updating_placeholder or
                self.disable_anim
        ):
            return super().resizeEvent(event)

        self.ensure_anim()
        assert self.anim

        if self.is_expanded and self._search_bar and self._search_bar.isVisible():
            if self.anim.state() != QPropertyAnimation.State.Running:
                self._search_bar.setGeometry(self.rect())
            else:
                self.anim.update_target_rect(self.rect())
        elif not self.is_expanded and self.anim.state() == QPropertyAnimation.State.Running:
            new_target = self.state_machine.query_placeholder_rect_safely()
            if new_target is not None:
                self.anim.update_target_rect(new_target)

        return super().resizeEvent(event)


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
    # noinspection SpellCheckingInspection
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
