#
""""""

from importlib.resources import files

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

from albuswall.ui.gui.service import ContentService
from albuswall.configue import UIConfig

from .content import Content
from .presenter import ContentPresenter, AlbumPresenter
from .titlebar import TitleBar
from .frame import Frame
from .album import AlbumInterface
# from .viewer import View

from ..utils.window_resizer import WindowResizer
from ..utils.disable_win11_round_corners import disable_round_corners
from ..utils.loggers import get_logger

__all__ = ['Window']

RESOURCE_PACKAGE = 'albuswall.resources'
DEFAULT_QSS_RESOURCE = 'default_theme_qss/main_window.qss'


class Window(QWidget):
    def __init__(self):
        super().__init__()

        self._logger = get_logger(self)
        self.container = None
        self.confs = None
        self.conf = None

        self._first_refresh = False

        self.window_resizer = None

        self.content = None
        self.titlebar = None
        self.frame = None
        self.album_interface = None
        self.viewer = None

        self.content_service = None
        self.content_presenter = None
        self.album_presenter = None

        self.setup_ui()

    def setup(self, container):
        self.container = container
        self.conf = container.get("configue")
        self.confs: UIConfig = self.conf.static.ui

        #
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowMaximizeButtonHint)

        self.setMinimumSize(8, 8)
        w, h = self.conf.dynamic.ui.window_size
        self.resize(w, h)

        #
        self.window_resizer = WindowResizer(
            self, self, False)

        # ---- 组装 View / Presenter / Service ----
        # 创建 Service 并注入依赖
        content_service = ContentService(self)
        content_service.setup(container)  # 初始化仓库与缩略图路径

        # 创建 Presenter，关联 View 与 Service
        content_presenter = ContentPresenter(self.content, content_service, parent=self)

        # 用配置中的默认视图初始化显示
        default_view_id = self.confs.default_current_view
        content_presenter.initialize_view(default_view_id)

        # 保存引用（可选，如果需要后续访问）
        self.content_service = content_service
        self.content_presenter = content_presenter
        # -----------------------------------------

        # ---- 组装 AlbumInterface 与 AlbumPresenter ----
        # 从容器获取 view_repo（假设已注册为 "view_repo"）
        view_repo = container.get("view_repo")
        if view_repo is None:
            raise RuntimeError("view_repo not registered in container")

        # 创建 Presenter 和界面
        self.album_presenter = AlbumPresenter(view_repo)
        self.album_interface = AlbumInterface(self.album_presenter, self)

        # 标题栏“相册”按钮 → 显示相册界面
        self.titlebar.btn_album_clicked.connect(
            lambda: self.album_presenter.show()
        )

        # 相册选择信号 → 切换视图并隐藏相册界面
        self.album_presenter.album_selected.connect(
            lambda album_id: (
                # 隐藏相册界面
                self.album_presenter.hide(),
                # 切换到所选视图
                self.content_presenter.change_view(album_id),
            )
        )

        #
        self._logger.debug("The UI setup completed.")

    def setup_ui(self):

        self.content = Content(self)
        self.titlebar = TitleBar(self)
        self.frame = Frame(self)
        # self.viewer = View(self)

        #
        self.content.lower()
        self.titlebar.setup()

        if __debug__:
            # noinspection SpellCheckingInspection
            self.setStyleSheet(
                files(RESOURCE_PACKAGE)
                .joinpath(DEFAULT_QSS_RESOURCE)
                .read_text(encoding='utf-8')
            )

    def showEvent(self, event):
        super().showEvent(event)
        if not self._first_refresh:
            if not self.conf.dynamic.ui.use_system_round_corners:
                hwnd = int(self.winId())
                disable_round_corners(hwnd)

            self.content.overscroll_top = self.titlebar.height()
            # self.content.unit_clicked.connect(
            #   lambda index: print(f"点击了单元：{index}")
            #   )

            self._first_refresh = True

    def resizeEvent(self, event):
        self.content.setGeometry(0, 0, self.width(), self.height())
        self.frame.setGeometry(0, 0, self.width(), self.height())
        self.titlebar.setGeometry(0, 3, self.width(), self.titlebar.height())
        self.album_interface.setGeometry(
            0, 18,
            self.width(), self.height() - 18
        )
        # self.viewer.setGeometry(
        #     0, 18,
        #     self.width(), self.height() - 18
        # )

    def closeEvent(self, event):
        self.hide()
