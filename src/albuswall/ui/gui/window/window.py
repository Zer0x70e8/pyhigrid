#
""""""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

from .content import Content
from .titlebar import TitleBar
from .frame import Frame
from .album import AlbumInterface
from .viewer import View
from .menu import Menu
from .source import Source

from ..utils.window_resizer import WindowResizer
from ..utils.loggers import get_logger

__all__ = ['Window']

# RESOURCE_PACKAGE = 'albuswall.resources'
# DEFAULT_QSS_RESOURCE = 'default_theme_qss/main_window.qss'


class Window(QWidget):
    content: Content
    titlebar: TitleBar
    frame: Frame
    album_interface: AlbumInterface
    viewer: View
    menu: Menu
    source: Source

    def __init__(self):
        super().__init__()

        self._logger = get_logger(self)
        self.container = None
        self.confs = None
        self.conf = None

        self._first_refresh = False

        self.window_resizer = None

        self.setup()
        self.setup_ui()

    def setup(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowMaximizeButtonHint)

        self.setMinimumSize(8, 8)

        self.window_resizer = WindowResizer(
            self, self, setup_flag=False
        )

    def setup_ui(self):

        self.content = Content(self)
        self.titlebar = TitleBar(self)
        self.frame = Frame(self)
        self.viewer = View(self)
        self.source = Source(self, target=self)
        self.menu = Menu(self)

        self.album_interface = AlbumInterface(self)

        #
        self.content.lower()
        self.titlebar.setup()
        self.source.hide()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._first_refresh:

            self.content.overscroll_top = self.titlebar.height()

            self._first_refresh = True

    def resizeEvent(self, event):
        self.content.setGeometry(0, 0, self.width(), self.height())
        self.frame.setGeometry(0, 0, self.width(), self.height())
        self.titlebar.setGeometry(0, 3, self.width(), self.titlebar.height())
        self.album_interface.setGeometry(
            0, 18,
            self.width(), self.height() - 18
        )
        self.viewer.setGeometry(
            0, 18,
            self.width(), self.height() - 18
        )
        self.source.setGeometry(0, 18, self.width(), self.height() - 18)

    def closeEvent(self, event):
        self.hide()
