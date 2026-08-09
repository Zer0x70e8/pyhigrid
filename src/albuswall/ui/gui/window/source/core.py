#
""""""

from PySide6.QtWidgets import QVBoxLayout

try:
    from ...widget.blur_overlay_label import BlurLabel
except ImportError:
    from albuswall.ui.gui.widget.blur_overlay_label import BlurLabel

class Source(BlurLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setup_ui()

    def setup_ui(self):
        pass


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QWidget

    app = QApplication(sys.argv)
    window = QWidget()
    widget = Source(window)
    _layout = QVBoxLayout(window)
    _layout.addWidget(widget)
    window.show()
    exit(app.exec())
