#
""""""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton
)
from PySide6.QtCore import Qt

from ..widget.blur_overlay_label import BlurLabel
from ..widget.image_viwer import ImageViewer
from ..widget.slide_up_scroll_container import SlideUpScrollContainer


class View(BlurLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 浮动容器（手动布局）
        self.top_bar_container = None
        self.bottom_bar_container = None
        self.browser_line = None

        # 内部布局（仅用于组织按钮，不再添加到根布局）
        self.top_bar_layout = None
        self.bottom_bar_layout = None

        # 按钮
        self.quit_button = None
        self.more_button = None
        self.info_button = None
        self.favourite_button = None
        self.adjust_button = None
        self.share_button = None
        self.trash_button = None

        # 核心滚动区域
        self.slide_up_container = None
        self.viewer = None

        self.setup_ui()

    def setup_ui(self):
        # ---------- 根布局（只放滚动区域）----------
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 滚动容器（背景层）
        self.slide_up_container = SlideUpScrollContainer(self)
        layout.addWidget(self.slide_up_container)

        # 图像查看器
        self.viewer = ImageViewer()
        self.slide_up_container.set_central_widget(self.viewer)
        self.viewer.drag_offset.connect(self._on_drag_offset)

        # ---------- 浮动控件创建 ----------
        # 顶部栏容器
        self.top_bar_container = QWidget(self)
        self.top_bar_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.top_bar_container.setStyleSheet("background: transparent;")

        self.top_bar_layout = QHBoxLayout(self.top_bar_container)
        self.top_bar_layout.setContentsMargins(8, 4, 8, 4)

        self.quit_button = QPushButton("✕", self.top_bar_container)
        self.more_button = QPushButton("⋯", self.top_bar_container)

        self.top_bar_layout.addWidget(self.quit_button)
        self.top_bar_layout.addStretch()
        self.top_bar_layout.addWidget(self.more_button)

        # 底部栏容器
        self.bottom_bar_container = QWidget(self)
        self.bottom_bar_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.bottom_bar_container.setStyleSheet("background: transparent;")

        self.bottom_bar_layout = QHBoxLayout(self.bottom_bar_container)
        self.bottom_bar_layout.setContentsMargins(8, 4, 8, 4)

        self.share_button = QPushButton("Share", self.bottom_bar_container)
        self.adjust_button = QPushButton("Adj", self.bottom_bar_container)
        self.info_button = QPushButton("ⓘ", self.bottom_bar_container)
        self.favourite_button = QPushButton("♥", self.bottom_bar_container)
        self.trash_button = QPushButton("🗑", self.bottom_bar_container)

        self.bottom_bar_layout.addWidget(self.share_button)
        self.bottom_bar_layout.addStretch()
        self.bottom_bar_layout.addWidget(self.adjust_button)
        self.bottom_bar_layout.addWidget(self.info_button)
        self.bottom_bar_layout.addWidget(self.favourite_button)
        self.bottom_bar_layout.addStretch()
        self.bottom_bar_layout.addWidget(self.trash_button)

        # 浏览器条（浮动）
        self.browser_line = QWidget(self)
        self.browser_line.setFixedHeight(4)
        self.browser_line.setStyleSheet("background: rgba(255,255,255,80); border-radius: 2px;")

        # ---------- 对象名（保持原有命名）----------
        self.setObjectName("ViewImage")

        self.top_bar_layout.setObjectName("ViewImageTopBarLayout")
        self.bottom_bar_layout.setObjectName("ViewImageBottomBarLayout")

        self.quit_button.setObjectName("ViewImageQuitButton")
        self.more_button.setObjectName("ViewImageMoreButton")
        self.info_button.setObjectName("ViewImageInfoButon")
        self.favourite_button.setObjectName("ViewImageFavouriteButton")
        self.adjust_button.setObjectName("ViewImageAdjustButton")
        self.share_button.setObjectName("ViewImageShareButton")
        self.trash_button.setObjectName("ViewImageTrashButton")

        self.browser_line.setObjectName("ViewImageBrowserLine")
        self.viewer.setObjectName("ViewImageContent")
        self.slide_up_container.setObjectName("ViewImageSlideUpContainer")

    def resizeEvent(self, event):
        """手动定位所有浮动组件，使其始终吸附在视图边缘"""
        super().resizeEvent(event)
        w = self.width()
        h = self.height()

        # 顶部栏：固定高度 40px
        top_h = 40
        self.top_bar_container.setGeometry(0, 0, w, top_h)

        # 底部栏：固定高度 40px
        bottom_h = 40
        self.bottom_bar_container.setGeometry(0, h - bottom_h, w, bottom_h)

        # 浏览器条：位于底部栏上方，高度 4px
        browser_h = 4
        self.browser_line.setGeometry(0, h - bottom_h - browser_h, w, browser_h)

        # 确保浮动控件始终在最上层
        self.top_bar_container.raise_()
        self.bottom_bar_container.raise_()
        self.browser_line.raise_()

    def _on_drag_offset(self, dx: int, dy: int):
        """将拖拽偏移量反向应用到内层滚动条，实现图像平移"""
        inner = self.slide_up_container.inner_scroll
        h_bar = inner.horizontalScrollBar()
        v_bar = inner.verticalScrollBar()
        h_bar.setValue(h_bar.value() - dx)
        v_bar.setValue(v_bar.value() - dy)
