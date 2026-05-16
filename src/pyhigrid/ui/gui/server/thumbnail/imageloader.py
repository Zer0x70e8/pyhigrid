#
"""This is background server, provided to gui.widget.virtual_scroll"""

from PySide6.QtCore import QObject, QRunnable, Signal


class ImageLoadTaskSignals(QObject):
    """Signals for the image loading task."""
    finished = Signal(object, object)  # number, QImage


class ImageLoadTask(QRunnable):
    """
    Worker task that calls the image provider function and emits the result.
    The task is executed in a thread pool to avoid blocking the GUI thread.
    """

    def __init__(self, number, func):
        """
        Args:
            number: The index/number that will be passed to the image generator.
            func: A callable that accepts a number and returns a QImage.
        """
        super().__init__()
        self.number = number
        self.func = func
        self._signals = ImageLoadTaskSignals()

    @property
    def signals(self):
        return self._signals

    def run(self):
        """Execute the image generation and emit the result via signal."""
        # func returns QImage (safe for cross-thread signals)
        image = self.func(self.number)
        self._signals.finished.emit(self.number, image)
