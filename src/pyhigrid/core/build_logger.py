#
""""""

import logging
from logging.config import fileConfig
from pathlib import Path
from typing import Optional, Union

from pyhigrid import __name__ as __main_package_name__
from pyhigrid.core import Container


LoggerName = __main_package_name__

TRACE = 5
logging.addLevelName(TRACE, "TRACE")

def setup_logging(
    configurator=None,
    log_conf_path: Optional[Union[str, Path]] = None,
    skip_configuration: bool = False,
    logger_name: str = "__main__"
) -> logging.Logger:
    """
    初始化日志系统。
    优先级：
    1. 若 skip_configuration=True，则仅使用 basicConfig（不加载文件）。
    2. 否则按以下顺序确定配置文件路径：
       - 直接传入的 log_conf_path
       - configurator 内置路径
       - 若两者都没有，使用 basicConfig 并保持默认级别
    3. 若提供了 configurator 且其包含 static.log.level，
       则该值将作为 logger 的最终级别（覆盖文件中设置）。
    """
    if skip_configuration:
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        logger = logging.getLogger(logger_name)
        return logger

    # 确定配置文件路径
    resolved_path: Optional[Path] = None
    if log_conf_path is not None:
        resolved_path = Path(log_conf_path)
    elif configurator is not None:
        resolved_path = (
            configurator.static.path.confs
            / configurator.static.file.log_conf_file
        )
    # 如果仍未得到路径，不使用文件配置
    if resolved_path is not None and resolved_path.is_file():
        if resolved_path.suffix == ".ini":
            fileConfig(resolved_path, disable_existing_loggers=False)
        else:
            # 这里可以扩展支持 dictConfig 等
            logging.basicConfig(
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                level=logging.INFO
            )
    else:
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )

    logger = logging.getLogger(logger_name)

    # 如果 configurator 提供了运行时级别，则强制应用（可选，注释掉则表示文件优先）
    if configurator is not None and hasattr(configurator.static.log, "level"):
        runtime_level = configurator.static.log.level
        if isinstance(runtime_level, int):
            logger.setLevel(runtime_level)
        else:
            # 尝试将字符串级别名（包括自定义的 TRACE）转为数字
            numeric_level = logging.getLevelName(runtime_level.upper())
            if isinstance(numeric_level, int):
                logger.setLevel(numeric_level)
            # 如果不是有效整数，说明级别名无效
            else:
                logger.warning("Invalid log level: %s", runtime_level)

    return logger

def register_logger(container: Container):
    container.register(
        "logger",
        lambda: setup_logging(
            configurator=container.get("configue"),
            logger_name=LoggerName
        )
    )
