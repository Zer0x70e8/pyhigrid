#
""""""

import logging

from pyhigrid.ui import UI_BASIC_LOGGER_NAME

def get_logger(obj: object, sub_module=None) -> logging.Logger:
    if sub_module is None:
        if isinstance(obj, type):
            logger_name = f"{UI_BASIC_LOGGER_NAME}.{obj.__name__}"
        else:
            logger_name = f"{UI_BASIC_LOGGER_NAME}.{type(obj).__name__}"
    else:
        logger_name = f"{UI_BASIC_LOGGER_NAME}.{sub_module}.{type(obj).__name__}"
    return logging.getLogger(logger_name)



