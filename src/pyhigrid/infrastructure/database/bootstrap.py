#
""""""

from typing import TYPE_CHECKING

from .connector import Connector

if TYPE_CHECKING:
    from pyhigrid.core import Container

def register_database(
        container  # type: Container
):
    container.register(
        "connector", lambda: Connector()
    )
