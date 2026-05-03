#
""""""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

from .content import Content
from .titlebar import TitleBar

from ..utils.window_resizer import WindowResizer
from ..utils.disable_win11_round_corners import disable_round_corners

from pyhigrid.configue import UIConfig

__all__ = ['Window']


class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.logger = None
        self.confs = None
        self.conf = None
        self.bg = None

        self._first_refresh = False

        self.window_resizer = None

        self.content = None
        self.titlebar = None

        self.setup_ui()

    def setup(self, logger, conf, confs, bg):
        self.logger = logger
        self.confs: UIConfig = confs
        self.conf = conf
        self.bg = bg

        #
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowMaximizeButtonHint)

        self.setMinimumSize(8, 8)
        w, h = self.conf.dynamic.ui.window_size
        self.resize(w, h)

        #
        self.window_resizer = WindowResizer(
            self, self, False)

        self.content.logger = logger

        #
        self.logger.debug("The UI setup completed.")

    def setup_ui(self):

        self.content = Content(self)
        self.titlebar = TitleBar(self)

        #
        self.content.lower()

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
        self.titlebar.setGeometry(0, 0, self.width(), self.titlebar.height())
