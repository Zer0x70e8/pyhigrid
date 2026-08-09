#
""""""

from typing import Dict
from dataclasses import dataclass
from typing import List

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QPixmap

from .content import Content
from .viewer import View
from ..service import ContentService
from albuswall.repository.view import ViewRepository


class ContentPresenter(QObject):
    image_clicked = Signal(str)

    def __init__(self, view: Content, service: ContentService, parent=None):
        super().__init__(parent)
        self._view = view
        self._service = service
        self._request_id = 0

        # Presenter 连接 View 的信号
        view.visible_range_changed.connect(self._on_visible_range_changed)
        # 连接 Content 的点击信号
        view.unit_clicked.connect(self._on_unit_clicked)


    def initialize_view(self, default_view_id: str):
        """首次加载时设置视图范围"""
        count = self._service.get_view_asset_count(default_view_id)
        self._view.update_max_item_index(count - 1)
        self._service.set_current_view(default_view_id)

    def change_view(self, view_id: str):
        """切换视图"""
        self._service.set_current_view(view_id)
        count = self._service.get_view_asset_count(view_id)
        self._view.update_max_item_index(count - 1)

    def _on_visible_range_changed(self, start: int, end: int):
        self._request_id += 1
        current_req = self._request_id
        actual_cell_size = self._view.cell_size  # 现在使用公共属性

        def on_result(data: Dict[int, bytes]):
            if current_req != self._request_id:
                return
            pixmaps = {}
            # 获得实际单元格尺寸，用于缩放
            target_size = self._view.cell_size
            for idx, png in data.items():
                pix = QPixmap()
                pix.loadFromData(png)
                # 如果生成的图片尺寸大于目标尺寸，进行高质量缩放
                if pix.width() != target_size or pix.height() != target_size:
                    pix = pix.scaled(target_size, target_size,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                pixmaps[idx] = pix
            self._view.set_pixmap_batch(pixmaps)

        # 直接传递实际尺寸给 Service，Service 内部做映射和去重
        self._service.request_thumbnails(start, end, actual_cell_size, on_result)

    def _on_unit_clicked(self, index: int):
        """将索引转换为原图路径，然后发射 image_clicked 信号"""
        path = self._service.get_asset_file_path(index)  # 需要 Service 提供此方法
        if path:
            self.image_clicked.emit(path)

@dataclass
class AlbumItemData:
    """用于界面展示的相册数据"""
    id: str
    title: str
    cover_thumb: str = ""


class AlbumPresenter(QObject):
    """
    相册界面的逻辑层（Presenter）
    职责：
        - 持有 view_repo，获取数据
        - 管理界面可见性状态
        - 处理用户动作（返回、编辑、选择相册）
        - 通知界面数据变化
    """
    visible_changed = Signal(bool)          # 界面可见性变化
    data_changed = Signal(list)             # 相册列表数据变化，传递 List[AlbumItemData]
    back_requested = Signal()               # 用户点击返回
    edit_requested = Signal()               # 用户点击编辑/添加
    album_selected = Signal(str)            # 用户选择某个相册，传递索引

    def __init__(self, view_repo: ViewRepository, parent=None):
        super().__init__(parent)
        self._view_repo = view_repo
        self._visible = False
        self._items: List[AlbumItemData] = []

    @property
    def visible(self) -> bool:
        return self._visible

    def show(self):
        """外部调用，显示相册界面并刷新数据"""
        self._refresh_data_from_repo()
        self._visible = True
        self.visible_changed.emit(True)

    def hide(self):
        """外部调用，隐藏相册界面"""
        self._visible = False
        self.visible_changed.emit(False)

    def go_back(self):
        """返回按钮处理：先隐藏自己，再通知外部导航返回"""
        self.hide()
        self.back_requested.emit()

    def select_album(self, album_id: str):
        """用户点击了某个相册，传出 UUID"""
        self.album_selected.emit(album_id)

    def _refresh_data_from_repo(self):
        """从仓库获取原始数据并转换为界面数据"""
        views = self._view_repo.get_views()
        self._items = [
            AlbumItemData(id=v.view_id, title=v.title, cover_thumb=v.cover_thumb)
            for v in views
        ]
        self.data_changed.emit(self._items)


class ViewPresenter(QObject):
    """
    控制图像查看器 (View) 的显示与隐藏，默认隐藏。
    对外提供 show_image / hide 方法，用于响应外部事件。
    """
    # 可选：当显示/隐藏时发出信号，方便其他模块监听
    shown = Signal()
    hidden = Signal()

    def __init__(self, view: View, parent=None):
        super().__init__(parent)
        self._view = view
        # 默认隐藏
        self._view.hide()

    def show_image(self, pixmap: QPixmap):
        """加载图像并显示 Viewer"""
        if pixmap.isNull():
            return
        self._view.viewer.load_pixmap(pixmap)   # View 内部持有 ImageViewer 实例
        self._view.show()
        self.shown.emit()

    def show_image_from_path(self, path: str):
        """便捷方法：从文件路径加载并显示"""
        pixmap = QPixmap(path)
        if pixmap.isNull():
            # 可选：记录日志
            return
        self.show_image(pixmap)

    def hide(self):
        """隐藏 Viewer"""
        self._view.hide()
        self.hidden.emit()

    def toggle(self, pixmap: QPixmap):
        """切换显示状态：若当前可见则隐藏，否则显示给定图像"""
        if self._view.isVisible():
            self.hide()
        else:
            self.show_image(pixmap)

    @property
    def is_visible(self) -> bool:
        return self._view.isVisible()

