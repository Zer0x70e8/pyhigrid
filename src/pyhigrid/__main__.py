#!/usr/bin/env python3
#
""""""

import sys
import logging
from logging.config import dictConfig

from configue import (Configue,
                      parse_env_config,
                      parse_args_to_config,
                      deep_merge
                      )
from core import Application

def build_config() -> dict:
    config = parse_env_config()  # All default keys are already included
    cli_overrides = parse_args_to_config()
    deep_merge(config, cli_overrides)

    return config


def main():
    # conf
    static_conf_dict = build_config()
    if __debug__:
        from pyhigrid.configue import UI_ENUM
        static_conf_dict["ui"]["ui"] = UI_ENUM.GUI

    configurator = Configue()
    configurator.static.load(static_conf_dict)
    #
    # print(configurator)

    # log
    log_conf_file_path = (configurator.static.path.confs /
               configurator.static.log.log_conf_file)
    if (log_conf_file_path is not None and
            (log_conf_file_path.is_file() and
             (log_conf_file_path.suffix == ".ini")
            )):
        logging.config.fileConfig(log_conf_file_path)
    else:
        # noinspection SpellCheckingInspection
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - "
                   "%(levelname)s - %(message)s"
        )

    logger = logging.getLogger(__name__)
    if configurator.static.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.info("Program started.")

    # bg
    bg = 1

    # ui
    from ui import import_ui
    ui_app = import_ui(configurator.static.ui.ui)(sys.argv)
    ui_app.setup(configurator, logger, bg)
    ui_app.show()

    # main
    app = Application(bg, ui_app, logger, configurator)
    end_code = app.exec()

    # end
    logger.info("Program ended.")
    return end_code

if __name__ == '__main__':
    sys.exit(main())
