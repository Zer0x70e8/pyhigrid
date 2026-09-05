#
""""""

from logging import getLogger

from PySide6.QtCore import QCoreApplication  # , QTimer
from PySide6.QtWidgets import QApplication

from .config import setup_config
from .window import Window, WindowPresenter
from .utils.disable_win11_round_corners import disable_round_corners

import albuswall
from albuswall import __title__, __author__
from albuswall.resources import qss
# from albuswall.core import Application as mainApplication
from albuswall.configue import Configue, UIConfig as StaticUIConfig

__all__ = ["Application"]


class Application(QApplication):
    logger = getLogger(f"{albuswall.__name__}.__ui__")

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
        self.conf: Configue = container.get("configue")
        self.confs: StaticUIConfig = self.conf.static.ui

        setup_config(self.conf)

        self.main_window = Window()
        self.main_window_presenter = WindowPresenter(self.main_window)
        self.main_window_presenter.setup(self.container)
        self.main_window.setStyleSheet(
            "\n\n".join(
                i.read_text(encoding='utf-8')
                for i in self.conf.dynamic.ui.qss_files
            )
        )
        self.logger.debug(
            f"Loaded {len(self.conf.dynamic.ui.qss_files)} qss file(s) for main window."
        )

        # if __debug__:
        #     self.main_window.setStyleSheet(
        #         qss.read_text(encoding='utf-8')
        #     )
        #     QTimer.singleShot(20, lambda: print(
        #         self.main_window_presenter.presenters["ingest_source_presenter"]
        #     ))


        if not self.conf.dynamic.ui.use_system_round_corners:
            hwnd = int(self.main_window.winId())
            disable_round_corners(hwnd)

    def show(self):
        self.main_window.show()

    def exec(self):
        end_code = super().exec()
        # mainApplication.instance().container.reg("ui_end_code", lambda: end_code)
        return end_code
