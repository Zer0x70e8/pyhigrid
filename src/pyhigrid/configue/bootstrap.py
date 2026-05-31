#
""""""

from .utils import parse_env_config, parse_args_to_config, deep_merge
from .required_conf_table import UI as UI_ENUM


def build_configue():
    from .configue import Configue
    # build
    static_conf = parse_env_config()
    cli_overrides = parse_args_to_config()
    deep_merge(static_conf, cli_overrides)

    # test
    if __debug__:
        static_conf["ui"]["ui"] = UI_ENUM.GUI

    #
    configurator = Configue()
    configurator.static.load(static_conf)

    return configurator

def register_configue(container):
    # 依赖于 database, logger 等
    container.register(
        "configue",
        build_configue
    )

# alias
register = register_configue
