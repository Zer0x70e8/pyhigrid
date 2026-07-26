#!/usr/bin/env python3
"""Configuration loading from environment variables."""

import os
import copy
from pathlib import Path
from typing import (
    List, Tuple, Any, Generator,
    Optional, Union, Protocol
)

from ..required_conf_table import TABLE, TYPE_MAP, UI, TWO_NUM_TYPE
from ..exceptions import ConfigError

__all__ = ["parse_env_config", "update_config_from_env"]

class TraceLogger(Protocol):
    def trace(self, msg, *args, **kwargs) -> None: ...
    def debug(self, msg, *args, **kwargs) -> None: ...
    def info(self, msg, *args, **kwargs) -> None: ...
    def error(self, msg, *args, **kwargs) -> None: ...

# Helper functions
def _parse_bool(value: str) -> bool:
    """Parse a boolean from a string (case-insensitive)."""
    v = value.strip().lower()
    if v in ("true", "1", "yes", "on"):
        return True
    if v in ("false", "0", "no", "off"):
        return False
    raise ValueError(f"Cannot parse as boolean: '{value}'")

def _parse_two_num(value: str) -> Tuple[int, int]:
    """Parse a string 'x,y' into a tuple of two integers."""
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 2:
        raise ValueError(f"Expected two integers, got: '{value}'")
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        raise ValueError(f"Cannot parse '{value}' as two integers")

def _convert_value(raw: str, target_type: Any, logger=None) -> Any:
    """Convert a raw string to the target type, optionally logging trace details."""
    if logger:
        logger.trace("[Env] Converting raw value %r to %s", raw, target_type.__name__)
    if target_type == bool:
        return _parse_bool(raw)
    if target_type == int:
        return int(raw)
    if target_type == float:
        return float(raw)
    if target_type == str:
        return raw
    if target_type == Path:
        return Path(raw)
    if target_type == UI:
        try:
            return UI[raw]
        except KeyError:
            for member in UI:
                if member.value == raw:
                    if logger:
                        logger.trace("[Env] Matched UI enum by value: %s -> %s", raw, member)
                    return member
            raise ValueError(f"Invalid UI value: '{raw}'")
    if target_type is TWO_NUM_TYPE:
        return _parse_two_num(raw)
    raise TypeError(f"Unsupported env var type: {target_type}")

def _deep_get(d: dict, keys: List[str], default=None):
    """Retrieve a nested value from a dict using a list of keys."""
    for key in keys:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            return default
    return d

def _deep_set(d: dict, keys: List[str], value, logger=None):
    """Set a value in a nested dict, creating intermediate dicts as needed."""
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value
    if logger:
        logger.trace("[Env] Setting config item %s = %r", ".".join(keys), value)

def _iter_env_keys(prefix: str, type_map: dict, parent_keys: Optional[List[str]] = None
                   ) -> Generator[Tuple[str, List[str]], None, None]:
    """Generate (env_var_name, key_path) pairs by walking the type_map."""
    if parent_keys is None:
        parent_keys = []
    for key, subtype in type_map.items():
        if isinstance(subtype, dict):
            yield from _iter_env_keys(prefix, subtype, parent_keys + [key])
        else:
            var_name = prefix + "_".join(parent_keys + [key]).upper()
            yield var_name, parent_keys + [key]

def _deep_merge(base: dict, overrides: dict, logger=None):
    """Recursively merge overrides into base, logging changes."""
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            if logger:
                logger.trace("[Env] Recursively merging dict key: %s", key)
            _deep_merge(base[key], value, logger)
        else:
            if logger:
                logger.trace("[Env] Overriding config item %s: %r -> %r", key, base.get(key), value)
            base[key] = value

# Main functions
def parse_env_config(
    base_config: Optional[dict] = None,
    type_map: Optional[dict] = None,
    prefix: Optional[str] = None,
    *,
    logger: Optional[Union[TraceLogger]] = None,
) -> dict:
    """
    Read configuration overrides from environment variables.
    Returns a dict containing only the fields that were actually set via environment.
    """
    if base_config is None:
        base_config = TABLE
    if type_map is None:
        type_map = TYPE_MAP

    env_override = base_config.get("env_override", {})
    if prefix is None:
        prefix = env_override.get("prefix", "PYHIGRID_")

    if logger:
        logger.debug("[Env] Starting to read config from environment variables")
        logger.trace("[Env] Using prefix: %s", prefix)
        logger.trace("[Env] Type map keys count: %d", len(type_map))

    env_overrides = {}

    for env_var, keys in _iter_env_keys(prefix, type_map):
        if logger:
            logger.trace("[Env] Checking env var %s -> config path %s", env_var, ".".join(keys))

        raw_value = os.environ.get(env_var)
        if raw_value is None:
            continue

        if logger:
            logger.debug("[Env] Found env var %s = %s", env_var, raw_value)

        target_type = _deep_get(type_map, keys)
        if logger:
            logger.trace("[Env] Target type: %s", target_type.__name__ if target_type else "unknown")

        try:
            value = _convert_value(raw_value, target_type, logger=logger)
        except Exception as e:
            if logger:
                logger.error("Failed to parse env var %s: %s", env_var, e)
            raise ConfigError.from_env(
                message=f"Cannot convert value to {target_type.__name__}",
                key=env_var,
                value=raw_value,
                cause=e,
            ) from e

        _deep_set(env_overrides, keys, value, logger=logger)
        if logger:
            logger.info("[Env] Applied env override: %s = %r", ".".join(keys), value)

    if logger:
        logger.debug("[Env] Env parsing complete, %d overrides applied", len(env_overrides))
        logger.trace("[Env] Override details: %r", env_overrides)
    return env_overrides


def update_config_from_env(
    target_dict: Optional[dict] = None,
    *,
    logger: Optional[Union[TraceLogger]] = None,
) -> dict:
    """
    Override and update the given configuration dict with environment variables (in-place).
    """
    if logger:
        logger.debug("[Env] Starting config update from env")
        logger.trace("[Env] Original target config: %r", target_dict)

    new_conf = copy.deepcopy(target_dict if target_dict is not None else TABLE)
    if logger:
        logger.trace("[Env] Deep copy of base config complete, item count: %d", len(new_conf))

    overrides = parse_env_config(target_dict, logger=logger)
    _deep_merge(new_conf, overrides, logger=logger)

    if target_dict is not None:
        target_dict.clear()
        target_dict.update(new_conf)
        if logger:
            logger.info("[Env] Target config updated (in-place)")
    else:
        TABLE.clear()
        TABLE.update(new_conf)
        if logger:
            logger.info("[Env] Module-level TABLE updated")

    if logger:
        logger.debug("[Env] Env config update complete")
    return new_conf
