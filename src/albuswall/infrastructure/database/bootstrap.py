#
""""""

from pathlib import Path
from typing import TYPE_CHECKING

from .connector import Connector

if TYPE_CHECKING:
    from albuswall.core import Container
    from albuswall.configue import Configue

def register_database(
        container  # type: Container
):
    # db_file = lambda conf: (conf.static.path.confs / conf.static.file.album_db_file)
    # db_file = lambda _: Path(r"E:\myCode\py\albuswall\assets\my_library.db")
    db_file = lambda _: Path(r"/data/myCode/py/pyhigrid/assets/my_library.db")

    # noinspection PyTypeChecker
    container.register(
        "db", lambda: Connector(
            db_file(
                container.get("configue")  # type: Configue
            )
        )
    )
