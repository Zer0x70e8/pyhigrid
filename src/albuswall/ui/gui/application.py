#
""""""
from logging import getLogger

from PySide6.QtCore import QCoreApplication  # , QTimer
from PySide6.QtWidgets import QApplication

from .window import Window, WindowPresenter
from .utils.disable_win11_round_corners import disable_round_corners

from albuswall import __name__ as __main_package_name__
from albuswall.__about__ import __title__, __author__
# from albuswall.core import Application as mainApplication
from albuswall.configue import UIConfig, Namespace

__all__ = ["Application"]


class Application(QApplication):
    logger = getLogger(f"{__main_package_name__}.__ui__")

    def __init__(self, argv):
        super().__init__(argv)

        # self.setQuitOnLastWindowClosed(False)

        self.main_window = None
        self.main_window_presenter = None

        self.container = None
        self.conf = None
        self.confs = None

    def setup(self, container):
        QCoreApplication.setOrganizationName(__author__)
        QCoreApplication.setApplicationName(__title__)

        self.container = container
        self.conf = container.get("configue")
        self.confs: UIConfig = self.conf.static.ui

        self.setup_confs()

        self.main_window = Window()
        self.main_window_presenter = WindowPresenter(self.main_window)
        self.main_window_presenter.setup(self.container)
        # QTimer.singleShot(20, lambda: print(
        #     self.main_window_presenter.presenters["ingest_source_presenter"]
        # ))

        if not self.conf.dynamic.ui.use_system_round_corners:
            hwnd = int(self.main_window.winId())
            disable_round_corners(hwnd)

    def setup_confs(self):
        dynamic_conf = Namespace()
        dynamic_conf.use_system_round_corners = (
            self.confs.use_system_round_corners)
        dynamic_conf.window_size = (
            self.confs.default_window_size
        )

        self.conf.dynamic.ui = dynamic_conf

    def show(self):
        self.main_window.show()

    def exec(self):
        end_code = super().exec()
        # mainApplication.instance().container.reg("ui_end_code", lambda: end_code)
        return end_code
