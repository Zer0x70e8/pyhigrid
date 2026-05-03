#
""""""

import os
import sys
import tempfile
from pathlib import Path
from typing import Sequence, Annotated, Protocol, Tuple

from .ui_enum import UI
from pyhigrid.__about__ import __author__, __title__, __version__
from pyhigrid.resources import __file__ as resource_file

__all__ = ["UI",
           "get_user_config_dir",
           "TABLE", "TYPE_MAP", "TWO_NUM_TYPE",
           "UIConfig"
           ]


def get_user_config_dir(app_name: str, app_author: str = None) -> Path:
    """
    返回用户配置目录的 Path 对象。
    遵循各平台默认规则：
    - Windows: %APPDATA%/<author>/<app>  或  %APPDATA%/<app>
    - macOS:   ~/Library/Application Support/<app>
    - Linux:   ~/.config/<app>
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        if app_author:
            return Path(base) / app_author / app_name
        return Path(base) / app_name
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    else:  # Linux 及其他 Unix
        xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        return Path(xdg_config) / app_name


def get_user_data_dir(app_name: str, app_author: str = None) -> Path:
    """
    返回用户数据目录的 Path 对象。
    遵循各平台默认规则：
    - Windows: %APPDATA%/<author>/<app>  或  %APPDATA%/<app>
    - macOS:   ~/Library/Application Support/<app>
    - Linux:   $XDG_DATA_HOME/<app>      (默认 ~/.local/share/<app>)
    注意：许多应用在 Windows/macOS 上将数据和配置放在同一目录下。
    """
    if sys.platform == "win32":
        # Windows 中配置文件和数据通常共享 %APPDATA% 目录
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        if app_author:
            return Path(base) / app_author / app_name
        return Path(base) / app_name
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    else:
        xdg_data = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        return Path(xdg_data) / app_name


def get_cache_dir(app_name: str, app_author: str = None):
    """
    持久缓存目录
    """
    # 持久缓存 (跨平台) — 优先使用 platformdirs，失败时用标准库降级
    try:
        # noinspection PyUnusedImports
        from platformdirs import user_cache_dir
        persistent = Path(user_cache_dir(app_name, app_author))
    except ImportError:
        persistent = _fallback_cache_dir(app_name, app_author)

    return persistent


def get_temp_dir(app_name: str) -> Path:
    """
    临时缓存目录
    """
    # 临时缓存 — 系统临时目录 + 应用子文件夹
    temporary = Path(tempfile.gettempdir()) / app_name

    temporary.mkdir(parents=True, exist_ok=True)

    return temporary


def _fallback_cache_dir(app_name: str, app_author: str = None) -> Path:
    """不依赖第三方库时的手动实现，遵循各平台惯例"""
    import sys
    home = Path.home()

    if sys.platform == "win32":
        # Windows: %LOCALAPPDATA%\<author>\<app>\Cache
        base = os.environ.get("LOCALAPPDATA", home / "AppData" / "Local")
        if app_author:
            return Path(base) / app_author / app_name / "Cache"
        return Path(base) / app_name / "Cache"

    elif sys.platform == "darwin":
        # macOS: ~/Library/Caches/<app>
        return home / "Library" / "Caches" / app_name

    else:
        # Linux 等: 遵循 XDG_CACHE_HOME，默认 ~/.cache
        base = os.environ.get("XDG_CACHE_HOME", home / ".cache")
        return Path(base) / app_name


# =========
TWO_NUM_TYPE = Annotated[Sequence[int], "length=2"]

TABLE = {
    "debug": False,  # Open the debugger.

    # Arguments of the Python interpreter.
    "m": None,
    "O": None,

    "app": {
        "name": __title__,
        "author": __author__,
        "version": __version__,
    },

    "path": {
        "confs": get_user_config_dir(__title__, __author__),
        "cache": get_cache_dir(__title__, __author__),  # PersistentCache
        "data": get_user_data_dir(__title__, __author__),
        "resources": Path(resource_file),
        "temp": get_temp_dir(__title__ + "_tmp"),
    },

    "file": {  # It's just the name, not the full path.
        "log_conf_file": Path("logging.conf"),
    },

    "env_override": {
        "prefix": "PYHIGRID_",
    },

    "log": {
        "log_conf_file": Path("logging.conf"),
        "verbose": False,  # More log output.
        "quiet": False,  # Diable INFO log level output.
    },

    "ui": {
        "ui": UI.CLI,
        "default_theme": "default",
        "default_window_size": (800, 600),
        "default_tui_size": (80, 24),
        "use_system_round_corners": False,   # 是否启用 Windows 11 系统圆角，默认禁用（直角）
    },

}

TYPE_MAP = {
    "debug": bool,

    "m": str,
    "O": int,

    "log": {
        "verbose": bool,
        "quiet": bool,
        "log_conf_file": Path,
    },

    "path": {
        "confs": Path,
        "cache": Path,
        "data": Path,
        "resources": Path,
        "temp": Path,
    },

    "file": {
        "log_conf_file": Path,
    },

    "ui": {
        "ui": UI,
        "default_theme": str,
        "default_window_size": TWO_NUM_TYPE,
        "default_tui_size": TWO_NUM_TYPE,
        "use_system_round_corners": bool,
    },
}

class UIConfig(Protocol):
    ui: UI
    default_theme: str
    default_window_size: Tuple[int, int]
    default_tui_size: Tuple[int, int]
    use_system_round_corners: bool