#
""""""

import sys
import logging
# noinspection PyUnusedImports
from logging.config import fileConfig as logging_fileConfig
from pathlib import Path

from ._import import *


def setup_configure(logger=None) -> Configue:
    """构建并加载静态配置"""

    # build
    static_conf = parse_env_config()
    cli_overrides = parse_args_to_config()
    deep_merge(static_conf, cli_overrides)

    # test
    if __debug__:
        from pyhigrid.configue import UI_ENUM
        static_conf["ui"]["ui"] = UI_ENUM.GUI

    #
    configurator = Configue()
    configurator.static.load(static_conf)

    if logger is not None:
        configurator.logger = logger

    return configurator


def setup_logging(
        configurator=None,
        log_conf_path: Path | str=None,
        skip_configuration=False,
        logger_name: str="__main__"
) -> logging.Logger:
    """根据配置初始化日志系统"""
    if not skip_configuration:
        if configurator is None:
            if log_conf_path is None:
                raise RuntimeError(
                    "Configurator must be initialized before logging."
                )
            else:
                # log_conf_path = log_conf_path
                pass
        else:
            log_conf_path = (
                configurator.static.path.confs
                / configurator.static.log.log_conf_file
            )

    if log_conf_path.is_file() and log_conf_path.suffix == ".ini":
        logging_fileConfig(log_conf_path)
    else:
        logging.basicConfig(
            # level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    logger = logging.getLogger(logger_name)
    if configurator is not None and configurator.static.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    return logger


def setup_db(
        logger=None,
        configurator=None
) -> Database:
    db = Database()
    if configurator is None:
        on_bg_log_missing(db, logger)
    else:
        pass  # 暂时没有可配置功能

    return db

def setup_bg(
        logger=None,
        configurator=None
):
    pass

def setup_ui(
        configurator: Configue=None,
        logger: logging.Logger=None,
        argv: list[str] | None = None,
        auto_show: bool = True,
) -> UIApplication:
    """根据配置加载 UI，完成 setup 并显示"""
    if configurator is None or logger is None:
        raise RuntimeError("Config and logger must be ready before UI.")

    if argv is None:
        argv = sys.argv

    if __debug__:
        bg = None  # test

    ui_module = import_ui(configurator.static.ui.ui)
    ui_app = ui_module(argv)
    ui_app.setup(configurator, logger, bg)
    if auto_show:
        ui_app.show()

    return ui_app

def build_application(
        bg,
        ui: UIApplication,
        logger: logging.Logger,
        configurator: Configue,
) -> Application:
    """组装核心 Application 对象"""
    application = Application(
        bg=bg,
        ui=ui,
        logger=logger,
        configurator=configurator,
    )
    return application

def on_bg_log_missing(
        _: Database,
        logger: logging.Logger
) -> None:
    if logger is None:
        print("[WARNING] [Boot] Background logging is missing.")
    else:
        logger.warning("[Boot] Background logging is missing.")
