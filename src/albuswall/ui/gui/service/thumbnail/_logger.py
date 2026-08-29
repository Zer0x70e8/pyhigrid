#
""""""

from pathlib import Path
from logging import Logger

from albuswall.ui.gui.utils.loggers import get_logger

logger: Logger = get_logger(Path(__file__).parent.name, Path(__file__).parent.parent.name)