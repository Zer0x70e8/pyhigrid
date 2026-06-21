#
""""""

from logging import getLogger
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QBitmap, QPainter

from pyhigrid import __name__ as __main_package_name__
from pyhigrid.core.bootstrapper.container import Container
from pyhigrid.repository.view_asset import ViewAssetRepository

from ..widget.virtual_scroll import VirtualScrollWidget
from ..server.thumbnail.provider import AssetImageProvider


class Content(VirtualScrollWidget):
    item_double_clicked = Signal(int)
    item_selection_changed = Signal(int, bool)   # index, selected

    def __init__(self, parent=None):
        super().__init__(parent)

        self._logger = getLogger(
            f"{__main_package_name__}.__ui__."
            f"{type(self.parent()).__name__}."
            f"{type(self).__name__}"
        )
        self._boot_container: Optional[Container] = None
        self._corner_radius = 24 + 3

        self._setup()

    def setup(self, boot_container= None):
        self._boot_container = boot_container
        thumbnails_path: Path = boot_container.get("configue").static.path.thumbnails
        if not thumbnails_path.exists():
            thumbnails_path.mkdir(parents=True)
        self._logger.debug(f"thumbnails_path={thumbnails_path}")
        self.provider = AssetImageProvider(
            boot_container.get("view_asset_repo"),  # type: ViewAssetRepository
            thumbnails_path=str(thumbnails_path)
        )
        self.provider.load_view("65000fc4-d6f6-56ae-b4cc-47717625b476")

    def _setup(self):
        self.setFocusPolicy(Qt.StrongFocus)   # 确保键盘滚动有效

    def _update_mask(self):
        """根据当前窗口大小生成圆角遮罩"""
        bitmap = QBitmap(self.size())
        bitmap.fill(Qt.color0)
        p = QPainter(bitmap)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(Qt.color1)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(self.rect(), self._corner_radius, self._corner_radius)
        p.end()
        self.setMask(bitmap)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update_mask()
