#!/usr/bin/env python3
#
""""""

import sys

from pyhigrid.core.application import Application
from pyhigrid.core.bootstrapper import Bootstrapper

def main():
    # ==== boot ====
    boot = Bootstrapper()

    # conf
    boot.setup_configure()

    # log
    boot.setup_logging(logger_name="__main__")
    logger = boot.logger
    logger.info("Program started.")

    # bg
    boot.setup_db()

    boot.bg = 1  # test
    boot.setup_ui(sys.argv)

    # app
    app: Application = boot.build_application()

    # exec
    end_code = app.exec()
    logger.info("Program ended.")
    return end_code

if __name__ == '__main__':
    sys.exit(main())
