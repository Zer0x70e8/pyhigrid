#
"""命令包：动态注册所有子命令"""
import logging
import importlib

logger = logging.getLogger(__name__)

# 定义所有命令名称
COMMANDS = ["init", "import_", "view", "edit", "get", "album", "trash"]


def register_all(subparsers):
    """遍历命令列表，动态导入并注册"""
    for cmd in COMMANDS:
        # noinspection PyBroadException
        try:
            # 动态导入 albuswall_cli.commands下的模块
            mod = importlib.import_module(f".{cmd}", package=__package__)
            mod.register(subparsers)
        except ImportError:
            logger.exception(f"Failed to import command '{cmd}'")
        except Exception:
            logger.exception(f"Failed to register command '{cmd}'")
