#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""""""

import sys
import gc
import logging
import traceback

from pyhigrid import __name__ as __main_package_name__
from pyhigrid.core import Application, Container
from pyhigrid.core.build_logger import register_logger
from pyhigrid.configue import register_configue
from pyhigrid.infrastructure.database import register_database
from pyhigrid.repository import register_repository
from pyhigrid.ui.bootstrap import register_ui

def main_():
    # container
    container = Container()

    # app
    app: Application = Application()
    app.container = container

    # conf
    register_configue(container)

    # log
    register_logger(container)

    #
    container.reg("ui_end_code", lambda: end_code)
    container.get("logger")  # Load immediately.
    root_logger: logging.Logger = logging.getLogger(__main_package_name__)
    root_logger.info("Program starting.")

    # db
    register_database(container)

    # repo
    register_repository(container)

    # gc freeze
    gc.collect()
    gc.freeze()

    # # bg
    #

    # ui
    register_ui(container)

    # exec
    end_code = app.exec()
    root_logger.info("Program ended.")
    gc.unfreeze()

    return end_code

def main():
    end_code = -1
    # noinspection PyBroadException
    try:
        end_code = main_()
    except KeyboardInterrupt:
        end_code = -1
    except Exception:
        traceback.print_exc()
        end_code = -1
    finally:
        return end_code

if __name__ == '__main__':
    sys.exit(main())
