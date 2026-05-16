#
""""""

from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QThreadPool, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel

from pyhigrid.ui.gui.server.thumbnail.imageloader import ImageLoadTask

if TYPE_CHECKING:
    # noinspection PyUnusedImports
    from .widget_basic import VirtualScrollWidgetBasic
    # noinspection PyUnusedImports
    from ...server.thumbnail.provider import AssetImageProvider


class Cell(QLabel):
    clicked = Signal(int)  # index

    def __init__(self, parent: "VirtualScrollWidgetBasic"):
        super().__init__(parent)

        # Qt about
        self.setScaledContents(True)  # Scale the pixmap to fill the label

        #
        self._index: Optional[int] = None  # The index this unit is currently showing (or assigned)]
        # Callable that generates a QImage given an index
        self._provider: Optional["AssetImageProvider"] = None
        self._pool = QThreadPool.globalInstance()
        self._active_task = None  # 跟踪当前加载任务

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, idx):
        """
        Assign a new index and initiate asynchronous image loading.
        If no image provider is set, this does nothing.

        Args:
            idx: The numeric index to display.
        """
        self._index = idx

        # 取消旧任务
        if self._active_task is not None:
            self._active_task.signals.finished.disconnect(self._on_image_loaded)
            self._active_task = None

        if self._provider and idx is not None:
            # 任务用 lambda 捕获 provider 和 idx，因为 get_thumbnail 是线程安全方法
            task = ImageLoadTask(idx, lambda i: self._provider.get_thumbnail(i))
            task.signals.finished.connect(self._on_image_loaded)
            self._active_task = task
            self._pool.start(task)

    @Slot(object, object)
    def _on_image_loaded(self, number, image: QImage):
        if number == self._index and not image.isNull():
            self.setPixmap(QPixmap.fromImage(image))
        self.setPixmap(QPixmap.fromImage(image))
        # 任务完成后清除引用（此时连接已触发，可以断开）
        self._active_task = None