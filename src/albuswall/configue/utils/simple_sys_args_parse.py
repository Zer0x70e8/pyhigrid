#!/usr/bin/env python3
"""Automatically generate an argument parser from the default config table (TABLE)
and type mapping (TYPE_MAP), and parse explicit overrides specified by the user
(higher priority than environment variables and defaults).
"""

import argparse
from pathlib import Path
from typing import (
    Sequence, Annotated, get_args, get_origin,
    Optional, Union
)

from albuswall.configue.logging_early import EarlyLogger
from ..required_conf_table import TABLE, TYPE_MAP, UI

__all__ = ["create_parser", "parse_args_to_config", "deep_merge"]

TWO_NUM_TYPE = Annotated[Sequence[int], "length=2"]


def _deep_set(d: dict, keys: list, value) -> None:
    """Set a value in a nested dict, creating intermediate dicts automatically."""
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


def _flatten_config(config_, type_map, prefix=""):
    """
    Recursively walk the config and type dicts, yielding tuples of
    (cli_flag, default, type_, help_str, path).
    path is a list of keys (e.g., ['log', 'verbose']) used to rebuild a nested dict later.
    """
    entries = []

    def walk(c, tm, pre, current_path):
        for key, value in c.items():
            full_key = f"{pre}.{key}" if pre else key
            cli_flag = "--" + full_key.replace(".", "-").replace("_", "-")
            path = current_path + [key]

            # Recurse into nested config (sub-dicts without a type mapping, or where the mapping is a dict)
            if (
                    isinstance(value, dict)
                    and (
                    key not in tm
                    or isinstance(tm.get(key), dict)
            )
            ):
                walk(value, tm.get(key, {}), full_key, path)
            else:
                # Leaf node
                typ = tm.get(key)
                if typ is None:
                    typ = type(value) if value is not None else str

                # Handle annotated types (like TWO_NUM_TYPE)
                origin = get_origin(typ)
                if origin is Annotated:
                    typ = get_args(typ)[0]  # extract base type

                help_str = f"Default: {value}"
                entries.append((cli_flag, value, typ, help_str, path))

    walk(config_, type_map, prefix, [])
    return entries


def _parse_two_int(arg: str):
    """Parse a '800,600' style string into a tuple of two integers."""
    parts = arg.split(",")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"Expected two integers separated by comma, e.g. 800,600, got: {arg!r}"
        )
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(f"Cannot convert {arg!r} to two integers")


def _build_type_converter(typ):
    """
    Return an argparse type= callable for the given type.
    - Path -> Path
    - UI -> UI (using the enum constructor)
    - Sequence[int] (TWO_NUM_TYPE) -> _parse_two_int
    - Other -> typ
    """
    if typ == Path:
        return Path
    if typ == UI:
        return UI
    origin = get_origin(typ)
    if origin is Sequence or origin is list:
        args = get_args(typ)
        if args == (int,) or args == (int,):
            return _parse_two_int
    # Handle Union / Optional types
    if origin is Union:
        types_in_union = get_args(typ)

        def union_converter(arg: str):
            for t in types_in_union:
                # Allow empty string or "none" for NoneType
                if t is type(None):
                    if arg == '' or arg.strip().lower() == 'none':
                        return None
                    continue
                try:
                    return t(arg)
                except (ValueError, TypeError):
                    continue
            raise argparse.ArgumentTypeError(
                f"Cannot convert {arg!r} to any type in {typ}"
            )
        return union_converter
    return typ


def _bool_flag_args(cli_flag, dest, default, help_str):
    """
    Return argparse argument specs for a boolean flag.
    Uses store_const with default=SUPPRESS so only explicit user input appears in the result.
    """
    base_kwargs = {
        "dest": dest,
        "default": argparse.SUPPRESS,  # crucial: not present unless explicitly passed
    }
    if default:
        no_flag = "--no-" + cli_flag[2:]
        return [
            (cli_flag, {**base_kwargs, "action": "store_const", "const": True,
                        "help": help_str + " (explicitly enable)"}),
            (no_flag, {**base_kwargs, "action": "store_const", "const": False,
                       "help": help_str + " (disable)"}),
        ]
    else:
        return [
            (cli_flag, {**base_kwargs, "action": "store_const", "const": True,
                        "help": help_str + " (enable)"}),
        ]


# Top-level keys that need manual handling
MANUAL_KEYS = {"m", "O"}

def create_parser(description="PyHiGrid command-line arguments", early_logger=None):
    parser = argparse.ArgumentParser(description=description)

    # Automatically generate all parameters except m and O
    entries = _flatten_config(TABLE, TYPE_MAP)

    if early_logger:
        early_logger.debug("[CLI]  Auto-generating %d leaf arguments", len(entries))

    for cli_flag, default, typ, help_str, path in entries:
        if early_logger:
            early_logger.trace("[CLI]  Adding argument: %s (type=%s)", cli_flag, typ)
        # Skip manually handled keys
        if len(path) == 1 and path[0] in MANUAL_KEYS:
            continue

        dest = "__".join(path)
        if typ == bool or typ is bool:
            for flag, kwargs in _bool_flag_args(cli_flag, dest, default, help_str):
                parser.add_argument(flag, **kwargs)
        else:
            convert = _build_type_converter(typ)
            parser.add_argument(
                cli_flag,
                type=convert,
                dest=dest,
                default=argparse.SUPPRESS,
                help=help_str,
            )

    # --- Manually add Python interpreter-style arguments ---
    # -m MODULE
    parser.add_argument(
        "-m", "--m",
        dest="m",
        nargs="?",  # optional argument
        const="__default__",  # default when no value given
        type=str,
        default=argparse.SUPPRESS,
        help="run library modules as a script (optional modules name)"
    )
    # -O : basic optimization
    parser.add_argument(
        "-O",
        dest="O",
        action="store_const",
        const=1,
        default=argparse.SUPPRESS,
        help="enable basic optimizations"
    )
    # -OO : stronger optimization (no value argument, activated by presence)
    parser.add_argument(
        "-OO",
        dest="O",
        action="store_const",
        const=2,
        default=argparse.SUPPRESS,
        help="discard docstrings in addition to -O optimizations"
    )

    # Keep the existing --env-prefix argument
    parser.add_argument(
        "--env-prefix",
        dest="env_override__prefix",
        default=argparse.SUPPRESS,
        help="override environment variable prefix (default read from config)",
    )

    return parser


def parse_args_to_config(args=None, logger: Optional[EarlyLogger] = None):
    parser = create_parser(early_logger=logger)
    if logger:
        logger.debug("[CLI]  [CLI]  Starting command-line argument parsing")
    try:
        ns = parser.parse_args(args)
    except SystemExit as e:
        # argparse raises SystemExit for --help, etc. – re-raise after logging if needed
        raise e
    except Exception as e:
        if logger:
            logger.error("[CLI]  Failed to parse command-line arguments: %s", e, exc_info=True)
        raise

    result = {}
    for dest, value in vars(ns).items():
        keys = dest.split("__")
        _deep_set(result, keys, value)
        if logger:
            logger.trace("[CLI]  CLI override: %s = %r", dest, value)

    if logger:
        logger.debug("[CLI]  CLI parsing complete, %d overrides", len(result))
    return result


def deep_merge(base: dict, override: dict):
    """Recursively merge override into base, with override taking precedence."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value


# Example usage
if __name__ == "__main__":
    # Simulate command-line input
    argv = [
        "prog",
        "--debug",
        "--log-verbose",
        "--ui-default-window-size", "1024,768",
        "--path-data", "/custom/data",
    ]
    # Print explicit overrides only
    overrides = parse_args_to_config(argv)
    print("Command-line overrides:")
    print(overrides)
