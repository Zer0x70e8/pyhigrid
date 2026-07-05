#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""""""

import sys
import logging
import traceback
import gc

import pyhigrid
from pyhigrid.core import Application, Container
from pyhigrid.core.build_logger import register_logger
from pyhigrid.configue import register_configue
from pyhigrid.infrastructure.database import register_database
from pyhigrid.repository import register_repository
from pyhigrid.ui.bootstrap import register_ui


# noinspection PyNoneFunctionAssignment
def main_():
    end_code = -1

    # container
    container = Container()

    # app
    app: Application = Application()
    app.container = container

    container.on(lambda: (
        container.get("logger"),
        logging.getLogger(pyhigrid.__name__)
        .info("Program starting."),
    ))

    # conf
    register_configue(container)  # configue

    # log
    register_logger(container)  # logger

    container.on(lambda: (
        container.reg("ui_end_code", lambda: end_code)
    ))

    # db
    register_database(container)  # db

    # repo
    register_repository(container)

    # # bg
    #

    # gc
    container.on(lambda: (
        (collected := gc.collect()),
        gc.freeze(),
        container.get("logger").info(
            f"Garbage collection freed {collected} objects, "
            f"freeze triggered."
        )
    ))

    # ui
    register_ui(container)

    # exec
    container.on( lambda:container.get("logger").info("Program ended."))
    end_code = app.exec()

    return end_code

def main():
    # end_code = -1
    # noinspection PyBroadException
    try:
        end_code = main_()
    except KeyboardInterrupt:
        end_code = 0
    except Exception:
        traceback.print_exc()
        end_code = -1
    return end_code

if __name__ == '__main__':
    sys.exit(main())
