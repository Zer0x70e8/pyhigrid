#
""""""

from PySide6.QtCore import Signal, Qt

from ..widget.virtual_scroll import VirtualScrollWidget

class Content(VirtualScrollWidget):
    item_double_clicked = Signal(int)
    item_selection_changed = Signal(int, bool)   # index, selected

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup()

    def _setup(self):
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setObjectName(type(self).__name__)

    @property
    def cell_size(self) -> int:
        """Actual size(pix) calculated dynamically."""
        return self._get_cell_size()
