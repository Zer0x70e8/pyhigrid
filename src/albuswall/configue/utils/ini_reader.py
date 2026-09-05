# 
"""
Lightweight INI configuration file reader.
Automatically converts string values to target types using a provided type mapping (type_map).
Supports generics such as Optional, List, Tuple, and allows external custom type parsers.
"""

from __future__ import annotations

import pprint
import configparser
import warnings
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union, get_origin, get_args
from ..logging_early import EarlyLogger


def load_ini(
        file_path: Path,
        type_map: Dict[str, Any],
        defaults: Optional[Dict[str, Any]] = None,
        converters: Optional[Dict[Any, Callable[[str], Any]]] = None,
        logger: Optional[EarlyLogger] = None,  # additional parameter for early logging
) -> Dict[str, Any]:
    """
    Read configuration from an INI file and convert each value according to type_map.

    Supports non-dictionary top-level keys in type_map (e.g., {"debug": bool}).
    These keys are read from key-value pairs without a section (and optionally
    from a [__default__] section) and placed under the "__default__" key in the result.

    Generic type support added:
    - Optional[X] : empty string becomes None, otherwise converted to X
    - List[X]     : comma-separated, each element converted to X
    - Tuple[X,Y]  : split by comma, converted to specified types (fixed length)
    - Custom converters can be registered via the converters parameter.

    Parameters
    ----------
    file_path : Path
        Path to the INI file.
    type_map : dict
        Type mapping, can be a mixed structure, e.g.:
            {"debug": bool, "app": {"name": str, ...}, ...}
        Non-dict top-level keys will be mapped to the "__default__" section.
    defaults : dict, optional
        Default values dictionary, structure matching type_map.
    converters : dict, optional
        Extra type converters in the format {type: parse_function}.
        Example: {MyType: lambda s: tuple(map(int, s.split(',')))}.
        Takes precedence over built-in generic parsing.
    logger : EarlyLogger, optional
        Logger for debug/trace output.

    Returns
    -------
    dict
        Configuration dictionary matching the type_map structure, with top-level keys
        placed under "__default__".
    """
    if logger:
        logger.trace(f"[INILoader] Start loading INI file: {file_path}")

    # 1. Separate top-level keys and section keys
    top_keys = {}
    sections = {}
    for key, value in type_map.items():
        if isinstance(value, dict):
            sections[key] = value
        else:
            top_keys[key] = value
    if logger:
        msg = f"[INILoader] Section map: {pprint.pformat(sections)}\nTop-level keys map: {top_keys}"
        [logger.trace(line) for line in msg.splitlines()]

    effective_map = sections.copy()
    if top_keys:
        effective_map["__default__"] = top_keys

    effective_defaults: Dict[str, Dict[str, Any]] = {}
    if defaults:
        for key, value in defaults.items():
            if isinstance(value, dict):
                effective_defaults[key] = value
            else:
                effective_defaults.setdefault("__default__", {})[key] = value

    # 2. Read the file
    try:
        raw_content = file_path.read_text(encoding="utf-8")
        if logger:
            logger.trace(f"[INILoader] File content read successfully, length: {len(raw_content)} characters")
    except Exception as e:
        if logger:
            logger.error(f"[INILoader] Failed to read file: {file_path} - {e}")
        raise

    config = configparser.ConfigParser()
    config.optionxform = lambda option: option

    try:
        config.read_string(raw_content)
    except configparser.MissingSectionHeaderError:
        if logger:
            logger.debug("[INILoader] INI file has no section headers, automatically adding [__default__] section")
        raw_content = "[__default__]\n" + raw_content
        config = configparser.ConfigParser()
        config.optionxform = lambda option: option
        config.read_string(raw_content)

    # 3. Process default data
    default_data = dict(config.defaults())
    if config.has_section("__default__"):
        default_data.update({k: config.get("__default__", k) for k in config.options("__default__")})
    if logger:
        logger.debug(f"[INILoader] Default data: {default_data}")

    result: Dict[str, Any] = {}

    # 4. Convert the "__default__" section
    if "__default__" in effective_map:
        fields = effective_map["__default__"]
        section_data: Dict[str, Any] = {}
        has_data = bool(default_data)

        if not has_data:
            if "__default__" in effective_defaults:
                section_data = effective_defaults["__default__"].copy()
                if logger:
                    logger.debug("Filling with __default__ defaults")
            else:
                section_data = {key: None for key in fields}
                if logger:
                    logger.debug("No __default__ data, setting all to None")
        else:
            for key, converter in fields.items():
                if key in default_data:
                    raw = default_data[key]
                    if logger:
                        logger.trace(
                            f"[INILoader] Converting default key {key!r}, raw value: {raw!r}, type: {converter}")
                    section_data[key] = _convert(raw, converter, converters, logger)
                elif "__default__" in effective_defaults and key in effective_defaults["__default__"]:
                    section_data[key] = effective_defaults["__default__"][key]
                    if logger:
                        logger.trace(
                            f"[INILoader] Key {key!r} using default value: {effective_defaults['__default__'][key]!r}")
                else:
                    section_data[key] = None
                    if logger:
                        logger.warning(f"[INILoader] Key {key!r} is not defined and has no default, set to None")
        result["__default__"] = section_data

    # 5. Process other sections
    for section, fields in effective_map.items():
        if section == "__default__":
            continue
        if not isinstance(fields, dict):
            raise ValueError(f"type_map section '{section}' value must be a dictionary")

        section_data = {}
        has_section = config.has_section(section)

        if not has_section:
            if section in effective_defaults:
                section_data = effective_defaults[section].copy()
                if logger:
                    logger.debug(f"[INILoader] Section [{section}] not found in file, using defaults")
            else:
                section_data = {key: None for key in fields}
                if logger:
                    logger.debug(
                        f"[INILoader] Section [{section}] not found in file and no defaults, setting all to None")
        else:
            for key, converter in fields.items():
                if config.has_option(section, key):
                    raw = config.get(section, key)
                    if logger:
                        logger.trace(
                            f"[INILoader] Converting section [{section}] key {key!r}, raw value: {raw!r}, type: {converter}"
                        )
                    section_data[key] = _convert(raw, converter, converters, logger)
                elif section in effective_defaults and key in effective_defaults[section]:
                    section_data[key] = effective_defaults[section][key]
                    if logger:
                        logger.trace(
                            f"[INILoader] Section [{section}] key {key!r} using default: {effective_defaults[section][key]!r}"
                        )
                else:
                    section_data[key] = None
                    if logger:
                        logger.warning(
                            f"[INILoader] Section [{section}] key {key!r} is not defined and has no default, set to None"
                        )
        result[section] = section_data

    # 6. Warn about unrecognized items
    _warn_unrecognized(config, effective_map, logger)

    if logger:
        msg = f"[INILoader] INI loading complete, result: {pprint.pformat(result)}"
        [logger.trace(line) for line in msg.splitlines()]

    return result


def _convert(
        raw: str,
        converter: Any,
        custom_converters: Optional[Dict[Any, Callable[[str], Any]]] = None,
        early_logger: Optional[EarlyLogger] = None
) -> Any:
    # Custom converter
    if custom_converters and converter in custom_converters:
        try:
            return custom_converters[converter](raw)
        except Exception as e:
            if early_logger:
                early_logger.warning(f"[INILoader] Custom converter {converter} failed: {raw!r}, error: {e}")
            return None

    origin = get_origin(converter)
    if origin is not None:
        args = get_args(converter)
        if origin is Union:
            non_none = [t for t in args if t is not type(None)]
            if not non_none:
                return None
            if len(non_none) == 1:
                inner_type = non_none[0]
                stripped = raw.strip()
                if stripped == "":
                    return None
                # noinspection PyBroadException
                try:
                    return _convert(stripped, inner_type, custom_converters, early_logger)
                except Exception:
                    return None
            else:
                for t in non_none:
                    # noinspection PyBroadException
                    try:
                        return _convert(raw.strip(), t, custom_converters, early_logger)
                    except Exception:
                        continue
                return None
        if origin is list:
            if not args:
                return raw
            item_type = args[0]
            stripped = raw.strip()
            if stripped == "":
                return []
            parts = [p.strip() for p in stripped.split(",") if p.strip()]
            return [_convert(p, item_type, custom_converters, early_logger) for p in parts]
        if origin is tuple:
            if not args:
                return raw
            stripped = raw.strip()
            if stripped == "":
                return ()
            parts = [p.strip() for p in stripped.split(",") if p.strip()]
            if len(args) == 2 and args[1] is ...:
                item_type = args[0]
                return tuple(_convert(p, item_type, custom_converters, early_logger) for p in parts)
            if len(parts) != len(args):
                warning_msg = (
                    f"[INILoader] Tuple conversion: expected {len(args)} elements, got {len(parts)}. "
                    f"[INILoader] Will truncate or pad with None."
                )
                if early_logger:
                    early_logger.warning(warning_msg)
                else:
                    warnings.warn(warning_msg)
            result_list = []
            for i, p in enumerate(parts):
                if i < len(args):
                    result_list.append(_convert(p, args[i], custom_converters, early_logger))
                else:
                    break
            while len(result_list) < len(args):
                result_list.append(None)
            return tuple(result_list)
        raise TypeError(f"Unsupported generic type: {converter}")

    # Basic types
    if converter is bool:
        return raw.strip().lower() in ("true", "1", "yes", "on")
    if converter is int:
        return int(raw)
    if converter is float:
        return float(raw)
    if converter is str:
        return raw
    if converter is Path:
        return Path(raw)
    if callable(converter):
        return converter(raw)
    raise TypeError(f"Unhandled converter type: {type(converter)} (value: {converter})")


def _warn_unrecognized(
        config: configparser.ConfigParser,
        effective_map: Dict[str, Any],
        early_logger: Optional[EarlyLogger] = None
) -> None:
    """Warn about unmapped sections/keys in the INI file (using logger or falling back to warnings)."""
    for section in config.sections():
        if section == "__default__":
            continue
        if section not in effective_map:
            msg = f"[INILoader] INI file contains undefined section [{section}], it will be ignored."
            if early_logger:
                early_logger.warning(msg)
            else:
                warnings.warn(msg)
        else:
            defined_keys = set(effective_map[section].keys())
            actual_keys = set(config.options(section))
            extra = actual_keys - defined_keys
            if extra:
                msg = f"[INILoader] Section [{section}] contains undefined keys: {extra}, they will be ignored."
                if early_logger:
                    early_logger.warning(msg)
                else:
                    warnings.warn(msg)
