#
""""""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyhigrid.core import Container

from .view import ViewRepository
from .view_asset import ViewAssetRepository

_map = {
    "view_repo": ViewRepository,
    "view_asset_repo": ViewAssetRepository,
}

def register_repository(
        container  # type: Container
):
    for name, cls in _map.items():
        container.register(
            name, lambda: cls(container.get("db"))
        )