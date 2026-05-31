#
""""""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from pyhigrid.ui.gui.window.window import Window

from pyhigrid.__about__ import __title__, __author__
# from pyhigrid.core import Application as mainApplication
from pyhigrid.configue import UIConfig, Namespace
from pyhigrid.configue.utils.logger_descriptor import LazyLogger

__all__ = ["Application"]


class Application(QApplication):
    logger = LazyLogger("__main__.__ui__")

    def __init__(self, argv):
        super().__init__(argv)

        # self.setQuitOnLastWindowClosed(False)

        self.main_window = None

        self.conf = None
        self.confs = None
        self.bg = None


    def setup(self, configurator):
        QCoreApplication.setOrganizationName(__author__)
        QCoreApplication.setApplicationName(__title__)

        self.conf = configurator
        self.confs: UIConfig = self.conf.static.ui

        self.setup_confs()

        self.main_window = Window()
        self.main_window.setup(self.logger,
                               self.conf,
                               self.confs,
                               self.bg
                               )

    def setup_confs(self):
        dynamic_conf = Namespace()
        dynamic_conf.use_system_round_corners =(
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
