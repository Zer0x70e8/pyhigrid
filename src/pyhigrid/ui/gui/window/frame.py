#
""""""

from PySide6.QtWidgets import QFrame
from PySide6.QtCore import Qt

class Frame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName(type(self).__name__)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)




