#
""""""

from pathlib import Path
from typing import Protocol, List

from albuswall.configue.required_conf_table import TWO_NUM_TYPE


class UIConfig(Protocol):
    theme_path: Path
    use_system_round_corners = bool
    window_size = TWO_NUM_TYPE
    qss_files: List[Path]
    icon_files = List[Path]
