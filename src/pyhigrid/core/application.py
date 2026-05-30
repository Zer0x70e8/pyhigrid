#
""""""

import logging
from typing import Optional

from .bootstrapper import Container
from pyhigrid.configue.utils.logger_descriptor import LazyLogger


class _Application:
    logger: logging.Logger = LazyLogger("__main__")

    def __init__(self):
        self.container: Optional[Container] = None


class Application(_Application):
    _instance = None
    _initialized = False
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if Application._initialized:
            return
        if self.__module__ != "pyhigrid.core.application":
            err_msg = (
                "[WARNING] There may be a singleton exception "
                f"in the main class. module: {self.__module__}"
            )
            if not self.logger.handlers:
                print(err_msg)
            else:
                self.logger.warning(err_msg)

        super().__init__()
        Application._initialized = True

    @classmethod
    def instance(cls):
        return cls._instance
