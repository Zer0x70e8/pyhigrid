#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""""""

import sys
import gc
import logging

from pyhigrid.core import Application, Container
from pyhigrid.core.build_logger import register_logger
from pyhigrid.configue import register_configue
from pyhigrid.infrastructure.database import register_database

def main():
    # container
    container = Container()

    # app
    app: Application = Application()
    app.container = container

    # conf
    register_configue(container)

    # log
    register_logger(container)

    root_logger: logging.Logger = logging.getLogger("__main__")
    root_logger.info("Program starting.")

    # db
    register_logger(container)

    # gc freeze
    gc.collect()
    gc.freeze()

    # # bg
    # boot.setup_db()
    #
    # boot.bg = 1  # test
    # boot.setup_ui(sys.argv)

    # exec
    end_code = 0
    # end_code = app.exec()
    root_logger.info("Program ended.")
    # gc.unfreeze()

    return end_code

if __name__ == '__main__':
    sys.exit(main())
