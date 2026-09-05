#
""""""

import shutil
import glob
import logging
from pathlib import Path
from typing import List

import albuswall
from albuswall.configue import Configue, Namespace
from albuswall.resources import theme
from albuswall.utils.resource import ensure_directory_from_template

try:
    from .types import UIConfig
except ImportError:
    from albuswall.ui.gui.config.types import UIConfig

_logger = logging.getLogger(f"{albuswall.__name__}.__ui__.config")


def setup(config: Configue):
    _namespace: UIConfig = Namespace()  # type: ignore
    config.dynamic.ui = _namespace
    confs = config.static.ui

    theme_path: Path = (
            config.static.path.confs /
            "theme" /
            confs.theme
    )
    qss_files: List[Path] = [
        theme_path / i for i in config.static.file.qss_files
    ]
    raw_icon_files = config.static.file.icon_files
    # icon_files: List[Path] = []

    #
    if not theme_path.is_dir():
        _logger.info("Theme path is not dir, will copy default theme now.")
        if theme_path.is_file():
            _logger.warning("Can't make theme dir, it's exisited.")
            qss_files = []
        else:
            theme_path.mkdir(parents=True, exist_ok=True)
            shutil.copytree(theme, theme_path, dirs_exist_ok=True)
            qss_files = [
                i for i in qss_files if i.is_file()
            ]

    icons_dir = theme_path / "icons"
    try:
        if ensure_directory_from_template(icons_dir, theme / "icon"):
            _logger.info(
                "Theme not have icon dir, will copy default template now."
            )
    except RuntimeError:
        _logger.warning("In theme directory, icon directory is not folder.")
    icon_files_count = sum(
        1 for _ in glob.iglob(str(icons_dir / raw_icon_files), recursive=True)
    )
    if icon_files_count > config.static.ui.max_icon_files_limit:
        e = "The number of icon files is greater than the limit: "
        f"{config.static.ui.max_icon_files_limit}"
        _logger.error(e)
        icon_files = []
    else:
        icon_files = glob.glob(str(icons_dir / raw_icon_files), recursive=True)

    #
    _namespace.use_system_round_corners = confs.use_system_round_corners
    _namespace.window_size = confs.default_window_size
    _namespace.theme_path = theme_path
    _namespace.qss_files = qss_files
    _namespace.icon_files = icon_files

    # print(_namespace)  # noqa
    # print(config)
    # print(config.dynamic)
    # print("After setting ui:")
    # print("dynamic.__dict__:", config.dynamic.__dict__)
    # print("dynamic.items():", list(config.dynamic.items()))
    # print("type(_namespace):", type(_namespace))
    # print("_namespace:", _namespace)
    # print("dynamic.ui:", config.dynamic.ui)
    # print(_namespace.icon_files)

    return _namespace
