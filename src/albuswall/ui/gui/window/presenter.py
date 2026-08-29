#
""""""

from typing import TYPE_CHECKING, TypedDict, Optional, Dict, List
from dataclasses import dataclass
from logging import Logger

from PySide6.QtCore import QObject, Qt, Signal, QModelIndex
from PySide6.QtGui import QPixmap

from .content import Content
from .viewer import View
from .source import Source
from .image_presenter import ImagePresenter
from ..utils.loggers import get_logger

from ..common.ingest_source import DetailRole, CardData
from ..models.ingest_source import IngestSourceModel
from ..models.ingest_source_detail import IngestSourceDetailModel
from ..delegates.source_card_delegate import SourceCardDelegate

from albuswall.domain.entities import IngestSourceEntity
from albuswall.repositories import (
    Repositories as AllRepositories, ViewRepository
)
from albuswall.services.ingest_source_service import IngestSourceService
from albuswall.configue import UIConfig
from albuswall.core.bootstrapper.container import Container
from albuswall.configue import Configue
from albuswall.__about__ import __title__ as __main_title__

if TYPE_CHECKING:
    from .window import Window


class Service(TypedDict):
    content_service: ImagePresenter
    ingest_source_service: IngestSourceService


class Repositories(AllRepositories):
    view: ViewRepository
    # ingest_source_repo: IngestSourceRepository


class WindowPresenter(QObject):
    container: "Container"
    conf: Configue
    confs: UIConfig
    logger: Logger
    service: Optional[Service]
    presenters: Optional[dict]
    repositories: Repositories

    def __init__(self, view: "Window", parent=None):
        super().__init__(parent)
        self._view: "Window" = view
        self.service = None
        self.presenters = None

    # noinspection PyNoneFunctionAssignment
    def setup(self, container: "Container"):
        self.container = container
        self.conf = container.get("configue")
        self.confs: UIConfig = self.conf.static.ui

        self._view.setWindowTitle(__main_title__)

        # get user
        self.logger = get_logger(self._view)
        view_repo = container.get("view_repo")
        # ingest_source_repo = container.get("ingest_source_repo")
        if view_repo is None:
            raise RuntimeError(
                "view_repo not registered in container"
            )

        content_service = ImagePresenter(self)
        content_service.setup(container)

        content_presenter = ContentPresenter(
            self._view.content,
            content_service,
            parent=self
        )
        view_presenter = ViewPresenter(
            self._view.viewer,
            parent=self
        )
        album_presenter = AlbumPresenter(view_repo)
        ingest_source_service = container.get("ingest_source_service")

        # setup
        content_presenter.initialize_view(
            str(self.confs.default_current_view)
        )
        self._view.album_interface.setup(album_presenter)
        album_presenter.hide()
        # 标题栏“相册”按钮 → 显示相册界面
        self._view.titlebar.btn_album_clicked.connect(
            lambda: album_presenter.show()
        )

        # 相册选择信号 → 切换视图并隐藏相册界面
        album_presenter.album_selected.connect(
            lambda album_id: (
                # 隐藏相册界面
                album_presenter.hide(),
                # 切换到所选视图
                content_presenter.change_view(album_id),
            )
        )

        # 当 Content 中的图片被点击时，获取其完整路径并显示
        # 通过 Presenter 的信号连接
        content_presenter.image_clicked.connect(
            view_presenter.show_image_from_path
        )

        ingest_source_presenter = IngestSourcePresenter(
            self._view.source,
            ingest_source_service,
            self
        )

        # 查看器退出按钮 → 隐藏查看器
        self._view.viewer.quit_button.clicked.connect(view_presenter.hide)

        self._view.menu.media_source_triggered.connect(lambda: (
            self._view.source.show(),
            self._view.source.raise_()
        ))

        self._view.titlebar.tool_bar.more_button.setMenu(self._view.menu)

        self._view.source.close_button.clicked.connect(self._view.source.hide)

        # last
        service_dict: Service = {
            "content_service": content_service,
            "ingest_source_service": ingest_source_service
        }
        self.service = service_dict
        self.presenters = {
            "content_presenter": content_presenter,
            "view_presenter": view_presenter,
            "album_presenter": album_presenter,
            "ingest_source_presenter": ingest_source_presenter
        }
        repositories: Repositories = {
            "view": view_repo,
            # "ingest_source_repo": ingest_source_repo,
        }
        self.repositories = repositories

        self.setup_config()

        self.logger.debug("The UI setup completed.")

    def setup_config(self):
        w, h = self.conf.dynamic.ui.window_size
        self._view.resize(w, h)

        # # 从配置文件或默认值初始化模型
        # self.presenters["ingest_source_detail_presenter"].set_source_path(
        #     self.confs...
        # )


class ContentPresenter(QObject):
    image_clicked = Signal(str)

    def __init__(
            self,
            view: Content,
            image_presenter: ImagePresenter,
            parent=None
    ):
        super().__init__(parent)
        self._view = view
        self._image_presenter = image_presenter
        self._request_id = 0

        # Presenter 连接 View 的信号
        view.visible_range_changed.connect(self._on_visible_range_changed)
        # 连接 Content 的点击信号
        view.unit_clicked.connect(self._on_unit_clicked)


    def initialize_view(self, default_view_id: str):
        """首次加载时设置视图范围"""
        count = self._image_presenter.get_view_asset_count(default_view_id)
        self._view.update_max_item_index(count - 1)
        self._image_presenter.set_current_view(default_view_id)

    def change_view(self, view_id: str):
        """切换视图"""
        self._image_presenter.set_current_view(view_id)
        count = self._image_presenter.get_view_asset_count(view_id)
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
        self._image_presenter.request_thumbnails(start, end, actual_cell_size, on_result)

    def _on_unit_clicked(self, index: int):
        """将索引转换为原图路径，然后发射 image_clicked 信号"""
        path = self._image_presenter.get_asset_file_path(index)
        if not path: return
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
        self.logger = get_logger(self._view)
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
            self.logger.debug(f"Show image: {path}")
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


class IngestSourcePresenter(QObject):
    """导入源管理界面的表现层，协调视图、模型与服务层。"""

    def __init__(self, view: Source, service: IngestSourceService, parent=None):
        super().__init__(parent)
        self._view = view
        self._service = service

        self._model_main = IngestSourceModel([], self)
        self._model_detail = IngestSourceDetailModel(self)
        self._model_detail = IngestSourceDetailModel(self)
        self._delegate = SourceCardDelegate()

        self._current_row = -1
        self._current_source_id: Optional[int] = None

        self.setup()

    # ---------- 初始化 ----------
    def setup(self):
        """初始化数据并连接信号，数据来自服务层。"""
        self._refresh_ui_from_service()   # 填充模型
        self._view.set_model(self._model_main, self._delegate)
        self._view.card_clicked.connect(self._on_card_clicked)
        self._view.apply_button.clicked.connect(self._save_current_detail)
        self._view.add_button.clicked.connect(self.add_new_source)
        self._model_detail.apply_to_widget(self._view.detail_widget)

    # ---------- 公开操作 ----------
    def set_data(self, items: List[dict]):
        """用外部数据完全替换当前列表。"""
        self._service.replace_all(items)
        self._refresh_ui_from_service()

    def add_new_source(self):
        """创建新的导入源并立即进入编辑状态。"""
        entity = self._service.create_source(
            title=self.tr("new ingest source"),  # 默认标题
            source_path="None"  # 默认路径，或使用其他占位符
        )
        if entity is None:
            return

        card_dict = self._entity_to_card_dict(entity)
        card_dict.pop("id", None)
        row = self._model_main.add_item(**card_dict)
        if row < 0:
            return

        index = self._model_main.index(row, 0)
        self._view.card_view.setCurrentIndex(index)
        self._on_card_clicked(index)

    def serialize_all(self) -> List[dict]:
        """导出所有数据为可序列化的字典列表。"""
        return self._service.export_all()

    # ---------- 私有槽函数 ----------
    def _on_card_clicked(self, index: QModelIndex):
        if not index.isValid():
            return

        card_data = self._model_main.data(index, DetailRole)
        if not card_data:
            return

        self._current_row = index.row()
        self._current_source_id = card_data.get("id")

        detail_dict = card_data.get("detail_data", {})
        self._model_detail.update_from_dict(detail_dict)
        self._model_detail.apply_to_widget(self._view.detail_widget)

    def _save_current_detail(self):
        if self._current_source_id is None:
            return

        self._model_detail.load_from_widget(self._view.detail_widget)
        detail_dict = self._model_detail.to_dict()

        updated_entity = self._service.update_source(
            self._current_source_id, **detail_dict
        )
        if updated_entity is not None:
            new_card_dict = self._entity_to_card_dict(updated_entity)
            self._model_main.update_item(self._current_row, new_card_dict)

    # ---------- 辅助方法 ----------
    @staticmethod
    def _entity_to_card_dict(entity: IngestSourceEntity) -> CardData:
        """将实体对象转换为 UI 模型所需的 CardData 字典。"""
        detail_data = {
            "title": entity.title,
            "description": entity.description,
            "tags": entity.tags,
            "source_path": entity.source_path,
            "file_types": entity.file_types,
            "file_type_check": entity.file_type_check,
            "subfolder_recursion": entity.subfolder_recursion,
            "subfolder_recursion_depth": entity.subfolder_recursion_depth,
            "scheduled_enabled": entity.scheduled_enabled,
            "update_mode": entity.update_mode,
            "scheduled_time": entity.scheduled_time,
            "interval_time": entity.interval_time,
            "device_trigger_enabled": entity.device_trigger_enabled,
            "target": entity.target_path,
            "auto_mount": entity.auto_mount,
            "mount_point": entity.mount_point,
        }

        card: CardData = {
            # "id": entity.id,
            "title": entity.title,
            "path": entity.source_path,      # 卡片上的“路径”对应 source_path
            "description": entity.description,
            "tags": entity.tags,
            "detail_data": detail_data,
        }
        return card

    def _refresh_ui_from_service(self):
        """从服务层重新加载所有数据并刷新主模型。"""
        entities = self._service.list_sources()
        card_dicts = [self._entity_to_card_dict(e) for e in entities]

        # 重新创建主模型（替代不存在的 reset 方法）
        self._model_main = IngestSourceModel(card_dicts, self)
        self._view.set_model(self._model_main, self._delegate)

        self._current_row = -1
        self._current_source_id = None
        self._view.card_view.clearSelection()
