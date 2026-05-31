#
""""""

import sys
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    # noinspection PyUnusedImports
    from pyhigrid.ui.gui.application import Application as UIApplication

    from pyhigrid.core import Container
    from pyhigrid.configue import Configue

ui_app: Optional["UIApplication"] = None

def register_ui(
        container  # type: Container
):
    container.register(
        "ui",
        lambda : setup_ui(container.get("configue"))
    )
    container.on(
        lambda: (
            container.reg(
                "ui_end_code",
                lambda: container.get("ui").exec()
            ),
            container.get("ui_end_code"),
        )[1]
    )
    # def boot_ui():
    #     # 这里才真正触发 UI 的创建
    #     ui = container.get("ui")
    #     ui.show()
    #     exit_code = ui.exec()
    #     container.reg("ui_end_code", exit_code)   # 保存退出码
    #     return exit_code   # 如果需要返回值
    #
    # container.on(boot_ui)

def setup_ui(
        configue  # type: Configue
):
    global ui_app
    from pyhigrid.ui import import_ui
    ui_cls = import_ui(configue.static.ui.ui)
    ui_app = ui_cls(sys.argv)
    ui_app.setup(configue)
    ui_app.show()
    return ui_app
