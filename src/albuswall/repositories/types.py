#
""""""

from typing import TypedDict

from .view import ViewRepository
from .view_asset import ViewAssetRepository
from .album import AlbumRepository
from .asset_edit import AssetEditRepository
from .trash import TrashRepository



class Repositories(TypedDict, total=False):
    view: ViewRepository
    view_asset: ViewAssetRepository
    album: AlbumRepository
    asset: AssetEditRepository
    trash: TrashRepository
