#
""""""

import logging

from .ui_enum import UI

import albuswall

UI_BASIC_LOGGER_NAME = f"{albuswall.__name__}.__ui__"
logger = logging.getLogger(UI_BASIC_LOGGER_NAME)

def import_ui(ui: UI):
    logger.debug(f"Trying to import: {ui.value}")
    match ui:
        # case UI.CLI:
        #     import .
        #     return None
        # case UI.TUI:
        #     import .
        #     return app
        case UI.GUI:
            from .gui import Application as App
            return App
        case _:
            raise RuntimeError(f"[UI] Not found: {ui.value}")

