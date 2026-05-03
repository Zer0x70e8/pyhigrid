#
"""
Configuration Unified Engine

configue: a lightweight configuration engine for static and dynamic sources.

Instead of another `config` or `configure`, this one argues with environment
variables, CLI args, and files — and unifies them under a single interface.

The name says it: config + argue, and the UE stands for Unified Engine.
"""

# main
from .configue import Configue
from .observable_value import ObservableValue
from .required_conf_table import (TABLE, TYPE_MAP, UI as UI_ENUM,
                                  UIConfig,
                                  get_user_config_dir)

# helpful
from .utils import (create_parser, parse_args_to_config,
                    parse_env_config, update_config_from_env,
                    deep_merge,
                    Namespace, FrozenNamespace,
                    )

__all__ = ["Configue",
           "ObservableValue",
           "TABLE", "TYPE_MAP", "UI_ENUM",
           "UIConfig",
           "get_user_config_dir",
           "create_parser", "parse_args_to_config",
           "parse_env_config", "update_config_from_env",
           "deep_merge",
           "Namespace", "FrozenNamespace",
           ]
