#
""""""

import logging
from logging.config import fileConfig as logging_fileConfig
from pathlib import Path

from pyhigrid.core import Container


def setup_logging(
        configurator=None,
        log_conf_path: Path | str=None,
        skip_configuration=False,
        logger_name: str="__main__"
) -> logging.Logger:
    """根据配置初始化日志系统"""
    if not skip_configuration:
        if configurator is None:
            if log_conf_path is None:
                raise RuntimeError(
                    "Configurator must be initialized before logging."
                )
            else:
                # log_conf_path = log_conf_path
                pass
        else:
            log_conf_path = (
                configurator.static.path.confs
                / configurator.static.log.log_conf_file
            )

    if log_conf_path.is_file() and log_conf_path.suffix == ".ini":
        logging_fileConfig(log_conf_path)
    else:
        logging.basicConfig(
            # level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    logger = logging.getLogger(logger_name)
    if configurator is not None and configurator.static.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    return logger

def register_logger(container: Container):
    container.register(
        "logger",
        lambda: setup_logging(
            configurator=container.get("configue")
        )
    )
