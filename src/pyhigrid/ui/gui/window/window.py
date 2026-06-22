#
""""""

from importlib.resources import files

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

from .content import Content
from .titlebar import TitleBar
from .frame import Frame

from ..utils.window_resizer import WindowResizer
from ..utils.disable_win11_round_corners import disable_round_corners
from ..utils.loggers import get_logger

from pyhigrid.configue import UIConfig

__all__ = ['Window']

RESOURCE_PACKAGE = 'pyhigrid.resources'
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

        #
        self.content.setup(container)

        #
        self._logger.debug("The UI setup completed.")

    def setup_ui(self):

        self.content = Content(self)
        self.titlebar = TitleBar(self)
        self.frame = Frame(self)

        #
        self.content.lower()

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

            self.content.layout_()
            self.content.overscroll_top = self.titlebar.height()
            # self.content.unit_clicked.connect(
            #   lambda index: print(f"点击了单元：{index}")
            #   )

            self._first_refresh = True

    def resizeEvent(self, event):
        self.content.setGeometry(0, 0, self.width(), self.height())
        self.frame.setGeometry(0, 0, self.width(), self.height())
        self.titlebar.setGeometry(0, 3, self.width(), self.titlebar.height())

    def closeEvent(self, event):
        self.hide()
