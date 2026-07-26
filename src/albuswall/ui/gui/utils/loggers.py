#
""""""

import logging

from albuswall.ui import UI_BASIC_LOGGER_NAME


def get_logger(
        obj: object | str,
        sub_module: object | str=None
) -> logging.Logger:
    if isinstance(obj, str):
        obj_name = obj
    elif isinstance(obj, type):
        obj_name = obj.__name__
    else:
        obj_name = type(obj).__name__
    if sub_module is None:
        logger_name = f"{UI_BASIC_LOGGER_NAME}.{obj_name}"
    else:
        if isinstance(sub_module, str):
            sub_module_name = sub_module
        elif isinstance(sub_module, type):
            sub_module_name = sub_module.__name__
        else:
            sub_module_name = type(sub_module).__name__
        logger_name = (
            f"{UI_BASIC_LOGGER_NAME}"
            f".{sub_module_name}"
            f".{obj_name}"
        )
    return logging.getLogger(logger_name)



