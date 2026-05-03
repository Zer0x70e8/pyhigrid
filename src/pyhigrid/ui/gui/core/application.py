#
""""""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from .window import Window

from pyhigrid.__about__ import __title__, __author__
from pyhigrid.configue import UIConfig, Namespace

__all__ = ["Application"]


class Application(QApplication):
    def __init__(self, argv):
        super().__init__(argv)

        self.main_window = None

        self.conf = None
        self.confs = None
        self.logger = None
        self.bg = None


    def setup(self, configurator, logger, bg):
        QCoreApplication.setOrganizationName(__author__)
        QCoreApplication.setApplicationName(__title__)

        self.conf = configurator
        self.confs: UIConfig = self.conf.static.ui
        self.logger = logger
        self.bg = bg

        self.setup_confs()

        self.main_window = Window()
        self.main_window.setup(self.logger.getChild("__ui__"),
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


