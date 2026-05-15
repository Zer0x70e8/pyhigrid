#
""""""

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QBitmap, QPainter

from ..widget.album_scroll_widget import AlbumScrollWidget, AssetImageProvider


class Content(AlbumScrollWidget):
    item_double_clicked = Signal(int)
    item_selection_changed = Signal(int, bool)   # index, selected
    def __init__(self, parent=None):
        super().__init__(parent)

        self._logger = None

        self._corner_radius = 25

        self._setup()

    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, value):
        self._logger = value

    def _setup(self):
        self.set_wheel_inverted(True)
        self.setFocusPolicy(Qt.StrongFocus)   # 确保键盘滚动有效

        self.provider = AssetImageProvider(None)

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
