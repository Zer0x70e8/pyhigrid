#
""""""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton
)

from ..widget.image_viwer import ImageViewer
from ..widget.slide_up_scroll_container import SlideUpScrollContainer


class View(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.top_bar_layout = None
        self.bottom_bar_layout = None

        self.quit_button = None
        self.more_button = None
        self.info_button = None
        self.favourite_button = None
        self.adjust_button = None
        self.share_button = None
        self.trash_button = None

        self.browser_line = None

        self.slide_up_container = None   # 替换原来的 QScrollArea
        self.viewer = None

        self.setup_ui()

    def setup_ui(self):
        # 根布局
        layout = QVBoxLayout(self)

        # 上下工具栏布局
        self.top_bar_layout = QHBoxLayout()
        self.bottom_bar_layout = QHBoxLayout()

        # 按钮
        self.quit_button = QPushButton(self)
        self.more_button = QPushButton(self)
        self.info_button = QPushButton(self)
        self.favourite_button = QPushButton(self)
        self.adjust_button = QPushButton(self)
        self.share_button = QPushButton(self)
        self.trash_button = QPushButton(self)

        # ---------- 核心：使用 SlideUpScrollContainer 替代普通滚动区 ----------
        self.slide_up_container = SlideUpScrollContainer(self)

        # 创建图像查看器（无父对象，稍后由 setCentralWidget 接管）
        self.viewer = ImageViewer()
        # 将 viewer 设为内层滚动区的内容
        self.slide_up_container.set_central_widget(self.viewer)

        # 连接拖拽偏移信号 → 驱动内层滚动条，实现图像平移
        self.viewer.drag_offset.connect(self._on_drag_offset)

        # 底部浏览器占位条（保持原有结构）
        self.browser_line = QWidget(self)

        # ---------- 布局组装 ----------
        # 顶部栏
        self.top_bar_layout.addWidget(self.quit_button)
        self.top_bar_layout.addStretch()
        self.top_bar_layout.addWidget(self.more_button)

        # 底部栏
        self.bottom_bar_layout.addWidget(self.share_button)
        self.bottom_bar_layout.addStretch()
        self.bottom_bar_layout.addWidget(self.adjust_button)
        self.bottom_bar_layout.addWidget(self.info_button)
        self.bottom_bar_layout.addWidget(self.favourite_button)
        self.bottom_bar_layout.addStretch()
        self.bottom_bar_layout.addWidget(self.trash_button)

        # 将各部件加入根布局（顺序与原来一致）
        layout.addLayout(self.top_bar_layout)
        layout.addWidget(self.slide_up_container)   # 占中间主要区域
        layout.addWidget(self.browser_line)
        layout.addLayout(self.bottom_bar_layout)

        # ---------- 对象名（保持原有命名风格）----------
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

    def _on_drag_offset(self, dx: int, dy: int):
        """将拖拽偏移量反向应用到内层滚动条，实现图像平移"""
        inner = self.slide_up_container.inner_scroll
        h_bar = inner.horizontalScrollBar()
        v_bar = inner.verticalScrollBar()
        # 鼠标向右移动 (dx > 0)，内容应向左移动，即滚动条值增加
        h_bar.setValue(h_bar.value() - dx)
        v_bar.setValue(v_bar.value() - dy)
