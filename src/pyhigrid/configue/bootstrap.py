#
"""
Configuration bootstrapping: load INI, environment, and CLI overrides,
merge them with priority, and register the resulting Configue instance.
"""

import copy
import logging
import traceback
from pathlib import Path

from .logging_early import EarlyLogger
from .utils import (
    parse_env_config, parse_args_to_config,
    load_ini,
    deep_merge
)
from .configue import Configue
from .required_conf_table import (
    UI as UI_ENUM, TYPE_MAP, TABLE, TWO_NUM_TYPE
)


early_logger = EarlyLogger("config_early", buffer_limit=2000)


def build_configue():
    """Build the application configuration by layering INI, environment, and CLI overrides."""
    ini_path = Path(TABLE['path']['confs']) / "conf.ini"

    converters = {
        UI_ENUM: lambda s: UI_ENUM.__members__[s.upper()],
        TWO_NUM_TYPE: lambda s: tuple(int(x) for x in s.split(',')),
    }

    # Check if configuration file exists
    if ini_path.exists():
        early_logger.info("Loading configuration from file: %s", ini_path)
        try:
            base_conf = load_ini(ini_path, TYPE_MAP, TABLE, converters=converters, logger=early_logger)
            early_logger.debug("INI configuration loaded successfully, %d entries", len(base_conf))
        except Exception:
            early_logger.error("INI loading failed: %s", traceback.format_exc())
            raise
    else:
        early_logger.warning("Configuration file not found: %s, using default configuration.", ini_path)
        base_conf = copy.deepcopy(TABLE)

    # Promote __default__ to top level, preserving original order (top-level keys first)
    if "__default__" in base_conf:
        default_items = base_conf.pop("__default__")
        base_conf = {**default_items, **base_conf}

    # 2. Read environment variable overrides
    env_overrides = parse_env_config(logger=early_logger)

    # 3. Read command-line overrides
    cli_overrides = parse_args_to_config(logger=early_logger)

    # 4. Merge layer by layer (priority: CLI > environment > INI > defaults)
    deep_merge(base_conf, env_overrides)
    deep_merge(base_conf, cli_overrides)

    # 5. Inject into Configue static configuration
    configurator = Configue()
    configurator.static.load(base_conf)

    return configurator

def register_configue(container):
    """Register the configuration builder and a flush callback with the DI container."""
    # Depends on database, logger, etc.
    container.register(
        "configue",
        build_configue
    )
    # Define a callback to flush buffered early logs into the official logger
    def flush_early_logs():
        # After bootstrap, the official logger is configured via logging
        # Retrieve the appropriate logger (e.g. root or app-specific)
        logger = logging.getLogger("pyhigrid.__conf__")
        # or logger = logging.getLogger("app")  # if a dedicated name exists

        # Attach early_logger to the official logger and clear the buffer
        early_logger.attach(logger)
        logger.debug("Early log buffer flushed to official logger")

    # Insert into bootstrap sequence; index should be after logging system init (e.g., index=5)
    container.on(flush_early_logs)

# alias
register = register_configue
