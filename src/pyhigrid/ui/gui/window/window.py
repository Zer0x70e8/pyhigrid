#
""""""

from logging import getLogger

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

from .content import Content
from .titlebar import TitleBar
from .frame import Frame

from ..utils.window_resizer import WindowResizer
from ..utils.disable_win11_round_corners import disable_round_corners

from pyhigrid import __name__ as __main_package_name__
from pyhigrid.resources import __file__ as __resources_file__
from pyhigrid.configue import UIConfig

__all__ = ['Window']


class Window(QWidget):
    def __init__(self):
        super().__init__()

        self._logger = getLogger(
            f"{__main_package_name__}.__ui__."
            f"{type(self).__name__}"
        )
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
            with open(
                    f"{__resources_file__[0:-12]}/default_theme_qss/main_window.qss",
                    "r", encoding="utf-8",

                    ) as qss:
                self.setStyleSheet(qss.read())

    def showEvent(self, event):
        super().showEvent(event)
        if not self._first_refresh:
            if not self.conf.dynamic.ui.use_system_round_corners:
                hwnd = int(self.winId())
                disable_round_corners(hwnd)

            self.content.layout_()
            self.content.overscroll_top = self.titlebar.height()
            # self.content.unit_clicked.connect(lambda index: print(f"点击了单元：{index}"))

            self._first_refresh = True

    def resizeEvent(self, event):
        self.content.setGeometry(0, 0, self.width(), self.height())
        self.frame.setGeometry(0, 0, self.width(), self.height())
        self.titlebar.setGeometry(0, 3, self.width(), self.titlebar.height())

    def closeEvent(self, event):
        self.hide()
