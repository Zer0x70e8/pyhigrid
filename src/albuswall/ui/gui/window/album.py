#
""""""

import os

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QSizePolicy, QFrame
)

from ..widget.blur_overlay_lable import BlurLabel
from ..widget.horizontal_square_scroll_area import HorizontalSquareScrollArea, Item
from .presenter import AlbumPresenter, AlbumItemData


class AlbumInterface(BlurLabel):
    """相册界面"""

    def __init__(self, presenter: AlbumPresenter, parent=None):
        super().__init__(parent, target=parent)
        self._presenter = presenter

        # UI 控件引用
        self.back_btn = None
        self.album_area = None
        self.album_widget = None
        self.album_edit_btn = None

        self.setup_ui()
        self._connect_presenter()

        # 初始状态（根据 presenter 的当前可见性设置）
        self._on_visibility_changed(self._presenter.visible)

    # ------------------------------------------------------------------
    #  UI 构建
    # ------------------------------------------------------------------
    def setup_ui(self):
        # 根布局
        main_layout = QVBoxLayout(self)
        main_layout.setObjectName("AlbumInterfaceMainLayout")

        # 返回按钮
        self.back_btn = QPushButton(self.tr("Back"), self)
        self.back_btn.setObjectName("AlbumBackButton")
        # 点击直接调用 Presenter 的方法
        self.back_btn.clicked.connect(self._presenter.go_back)

        # 相册区域
        self.setup_album_area()

        main_layout.addWidget(self.back_btn)
        main_layout.addWidget(self.album_widget)
        main_layout.addStretch()

    def setup_album_area(self):
        """构建相册列表区域（标题栏 + 滚动区域）"""
        self.album_widget = QFrame(self)
        self.album_widget.setObjectName("AlbumScrollAreaWidget")
        self.album_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # 横向方形滚动区域
        self.album_area = HorizontalSquareScrollArea(ratio=2.5, rows=2)
        self.album_area.setObjectName("AlbumScrollArea")
        self.album_area.setWidgetResizable(True)

        album_layout = QVBoxLayout(self.album_widget)
        album_layout.setObjectName("AlbumWidgetLayout")

        # ---- 标题栏 ----
        header_layout = QHBoxLayout()
        header_layout.setObjectName("AlbumHeaderLayout")

        title_label = QLabel(self.tr("Albums"), self)
        title_label.setObjectName("AlbumTitleLabel")

        self.album_edit_btn = QPushButton(self.tr("+"), self)
        self.album_edit_btn.setObjectName("AlbumEditButton")
        # 转发编辑动作
        self.album_edit_btn.clicked.connect(self._presenter.edit_requested.emit)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.album_edit_btn)

        album_layout.addLayout(header_layout)
        album_layout.addWidget(self.album_area)

    # ------------------------------------------------------------------
    #  与 Presenter 的连接
    # ------------------------------------------------------------------
    def _connect_presenter(self):
        """将 Presenter 的信号绑定到视图的响应方法"""
        self._presenter.visible_changed.connect(self._on_visibility_changed)
        self._presenter.data_changed.connect(self._rebuild_items)

    def _on_visibility_changed(self, visible: bool):
        """根据 Presenter 的状态控制界面显隐，并刷新模糊效果"""
        self.setVisible(visible)
        if visible:
            self._update_blur()  # 原有模糊逻辑

    def _rebuild_items(self, items: list[AlbumItemData]):
        """清空并重新填充相册项，同时绑定点击事件并设置封面"""
        if self.album_area is None:
            return

        # 清空已有项
        self.album_area.clear()
        # if hasattr(self.album_area, 'clear'):
        #     self.album_area.clear()
        # else:
        #     while self.album_area.widget().count():
        #         child = self.album_area.widget().takeAt(0)
        #         if child.widget():
        #             child.widget().deleteLater()

        # 根据数据创建新项
        for data in items:
            item = Item(data.title, self)
            if data.cover_thumb and os.path.isfile(data.cover_thumb):
                pixmap = QPixmap(data.cover_thumb)
                if not pixmap.isNull():
                    item.setPixmap(pixmap)

            item.set_album_id(data.id)
            item.selected.connect(self._presenter.select_album)

            self.album_area.addWidget(item)
