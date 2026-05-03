#
""""""

from PySide6.QtCore import Signal, Qt

# from PySide6.QtWidgets import QWidget

from ..widget.album_scroll_widget import VirtualScrolledWidget


class Content(VirtualScrolledWidget):
    item_double_clicked = Signal(int)
    item_selection_changed = Signal(int, bool)   # index, selected
    def __init__(self, parent=None):
        super().__init__(parent)

        self._logger = None

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
