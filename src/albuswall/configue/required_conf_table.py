#
""""""

import logging
from pathlib import Path
from uuid import UUID
from typing import (
    Sequence, Annotated, Protocol,
    Tuple, Optional, TypedDict, cast, List, Union
)

from .utils.platform_dir import (
    get_temp_dir, get_cache_dir,
    get_user_data_dir, get_user_config_dir
)

from albuswall.__about__ import __author__, __title__, __version__
from albuswall.resources import __file__ as resource_file
from albuswall.domain.constants import UUID_ALL_PHOTOS
from albuswall.ui.ui_enum import UI

__all__ = ["UI",
           "TABLE", "TYPE_MAP", "TWO_NUM_TYPE",
           "UIConfig"
           ]


# =========
class BuiltinAlbumDef(TypedDict, total=False):
    name: str
    uuid: Optional[UUID]

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
        "resources": Path(cast(str, resource_file)).parent,
        "temp": get_temp_dir(__title__ + "_tmp"),
        "thumbnails": get_cache_dir(__title__, __author__) / "thumbnails"
    },

    "file": {  # It's just the name, not the full path.
        "log_conf_file": Path("logging.conf"),
        "album_db_file": Path("album.db"),
        "qss_files": [Path("main_window.qss")],
        "icon_files": "*"
    },

    "env_override": {
        "prefix": "PYHIGRID_",
    },

    "log": {
        "level": logging.INFO,
    },

    "ui": {
        "ui": UI.CLI,
        "theme": "default",
        "default_theme": "default",
        "default_window_size": (800, 600),
        "default_tui_size": (80, 24),
        "use_system_round_corners": False,   # 是否启用 Windows 11 系统圆角，默认禁用（直角）
        "default_current_view": UUID_ALL_PHOTOS,
        "max_icon_files_limit": 100
    },

}

TYPE_MAP = {
    "debug": bool,

    "m": Optional[str],
    "O": Optional[int],

    "log": {
        "level": Union[int, str],
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
        "album_db_file": Path,
        "qss_files": List[Path],
        "icon_files": str | List[Path],
    },

    "ui": {
        "ui": UI,
        "theme": str,
        "default_window_size": TWO_NUM_TYPE,
        "default_tui_size": TWO_NUM_TYPE,
        "use_system_round_corners": bool,
        "default_current_view": UUID,
        "max_icon_files_limit": int
    },
}

class UIConfig(Protocol):
    ui: UI
    theme: str
    default_window_size: Tuple[int, int]
    default_tui_size: Tuple[int, int]
    use_system_round_corners: bool
    default_current_view: UUID
