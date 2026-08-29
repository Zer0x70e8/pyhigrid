#
""""""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from albuswall.core import Container

from .ingest_source import IngestSourceRepository
from .importer import ImportRepository
from .view import ViewRepository
from .view_asset import ViewAssetRepository
from .album import AlbumRepository
from .asset_edit import AssetEditRepository
from .trash import TrashRepository

_map = {
    "ingest_source_repo": IngestSourceRepository,
    "importer_repo": ImportRepository,
    "view_repo": ViewRepository,
    "view_asset_repo": ViewAssetRepository,
    "album_repo": AlbumRepository,
    "asset_edit_repo": AssetEditRepository,
    "trash_repo": TrashRepository,
}

def register_repository(
        container  # type: Container
):
    for name, cls in _map.items():
        container.register(
            name, lambda cls_=cls: cls_(container.get("db"))
        )
