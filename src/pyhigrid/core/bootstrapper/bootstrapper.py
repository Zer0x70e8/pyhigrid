#
""""""

from typing import Optional, Union

import logging

from ._import import *
from .setup import (
    setup_configure,
    setup_logging,
    setup_db,
    setup_bg,
    setup_ui,
    build_application
)


class Bootstrapper:
    def __init__(self):
        self.configurator: Optional[Configue] = None
        self.logger: Optional[logging.Logger] = None
        self.db: Optional[Database] = None
        self.bg: Optional = None
        self.ui_app: Optional[Union[UIApplication, ]] = None
        self.application: Optional[Application] = None

    def setup_configure(self, logger=None):
        self.configurator = setup_configure(
            logger=logger
        )

    def setup_logging(
            self,
            skip_configuration=False,
            logger_name: str="__main__"
    ):
        self.logger = setup_logging(
            self.configurator,
            skip_configuration=skip_configuration,
            logger_name=logger_name
        )

    def setup_db(self):
        self.db = setup_db(
            self.configurator,
            self.logger
        )

    def setup_bg(self):
        if self.configurator is None:
            raise RuntimeError(
                "Configurator must be initialized before run background."
            )
        self.bg = setup_bg(self.configurator, self.logger)

    def setup_ui(self, argv=None, auto_show=True):
        self.ui_app = setup_ui(
            self.configurator,
            self.logger,
            argv=argv,
            auto_show=auto_show
        )

    def build_application(self):
        self.application = build_application(
            bg=self.bg,
            ui=self.ui_app,
            logger=self.logger,
            configurator=self.configurator,
        )
        return self.application
