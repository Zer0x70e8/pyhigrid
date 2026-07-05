#
"""
Logging system initialization and registration.

Sets up logging based on a configuration file or defaults, applies runtime
level overrides from the configurator, and registers the logger in the DI container.
"""

import logging
from logging.config import fileConfig
from pathlib import Path
from typing import Optional, Union

import pyhigrid
from pyhigrid.core import Container


LoggerName = pyhigrid.__name__

TRACE = 5
logging.addLevelName(TRACE, "TRACE")

def setup_logging(
    configurator=None,
    log_conf_path: Optional[Union[str, Path]] = None,
    skip_configuration: bool = False,
    logger_name: str = "__main__"
) -> logging.Logger:
    """
    Initialize the logging system.

    Priority:
    1. If skip_configuration is True, only basicConfig is used (no file loaded).
    2. Otherwise, the config file path is determined by:
       - directly passed log_conf_path
       - configurator's built-in path
       - if neither is available, basicConfig is used with default level.
    3. If a configurator is provided and contains static.log.level,
       that value is applied as the logger's final level (overriding file config).
    """
    if skip_configuration:
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        logger = logging.getLogger(logger_name)
        return logger

    # Determine configuration file path
    resolved_path: Optional[Path] = None
    if log_conf_path is not None:
        resolved_path = Path(log_conf_path)
    elif configurator is not None:
        resolved_path = (
            configurator.static.path.confs
            / configurator.static.file.log_conf_file
        )
    # If no path resolved, skip file configuration
    if resolved_path is not None and resolved_path.is_file():
        if resolved_path.suffix == ".ini":
            fileConfig(resolved_path, disable_existing_loggers=False)
        else:
            # Extendable to support dictConfig etc.
            logging.basicConfig(
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                level=logging.INFO
            )
    else:
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )

    logger = logging.getLogger(logger_name)

    # If configurator provides a runtime level, apply it (overrides file config)
    if configurator is not None and hasattr(configurator.static.log, "level"):
        runtime_level = configurator.static.log.level
        if isinstance(runtime_level, int):
            logger.setLevel(runtime_level)
        else:
            # Try to convert string level name (including custom TRACE) to numeric
            numeric_level = logging.getLevelName(runtime_level.upper())
            if isinstance(numeric_level, int):
                logger.setLevel(numeric_level)
            else:
                logger.warning("Invalid log level: %s", runtime_level)

    return logger

def register_logger(container: Container):
    """Register the logger factory in the dependency injection container."""
    container.register(
        "logger",
        lambda: setup_logging(
            configurator=container.get("configue"),
            logger_name=LoggerName
        )
    )
