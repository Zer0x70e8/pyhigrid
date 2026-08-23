#
"""
Image Viewer with zoom and drag support using PySide6.
The image size changes according to the zoom factor, and the scroll area
allows panning when the image is larger than the viewport.
"""

import sys
from typing import cast

from PySide6.QtCore import Qt, QPoint, QEvent, Signal
from PySide6.QtGui import QPixmap, QPainter, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QScrollArea, QWidget, QFileDialog
)

__all__ = ["ImageViewer"]


class ImageViewer(QWidget):
    """A custom widgets that displays a zoomable and pannable image."""

    # Zoom limits and step
    MIN_ZOOM = 0.1
    MAX_ZOOM = 10.0
    ZOOM_STEP = 0.1

    drag_offset = Signal(int, int)  # 发出拖拽偏移量

    def __init__(self, parent=None):
        super().__init__(parent)
        # Internal pixmap to display
        self._pixmap = QPixmap()
        # Current zoom factor (1.0 = 100%)
        self._zoom_factor = 1.0
        # Drag state
        self._drag_global_start = QPoint()
        self._scroll_start_pos = QPoint()
        self._dragging = False
        # Reference to the parent scroll area (set externally)
        self._scroll_area = None
        self.setMinimumSize(10, 10)

    def set_scroll_area(self, scroll_area):
        """Store a reference to the QScrollArea that contains this widgets."""
        self._scroll_area = scroll_area

    # ---------- Drag control ----------
    # def _start_drag(self, global_pos):
    #     """Begin a panning operation. Records the starting mouse position
    #     and current scroll bar values, then installs a global event filter
    #     to capture mouse move and release events anywhere."""
    #     self._drag_global_start = global_pos
    #     if self._scroll_area:
    #         h_bar = self._scroll_area.horizontalScrollBar()
    #         v_bar = self._scroll_area.verticalScrollBar()
    #         self._scroll_start_pos = QPoint(h_bar.value(), v_bar.value())
    #     self._dragging = True
    #     # Use ClosedHandCursor via CursorShape enum (eliminates IDE warning)
    #     self.setCursor(Qt.CursorShape.ClosedHandCursor)
    #     # Install event filter on the application to track mouse events globally.
    #     # QApplication.instance() may return None according to type stubs,
    #     # so we add a safety check (it will always exist when running).
    #     app = QApplication.instance()
    #     if app is not None:
    #         app.installEventFilter(self)
    #
    # def _stop_drag(self):
    #     """End the panning operation, remove the global event filter,
    #     and restore the cursor."""
    #     if self._dragging:
    #         self._dragging = False
    #         # Use ArrowCursor via CursorShape enum
    #         self.setCursor(Qt.CursorShape.ArrowCursor)
    #         app = QApplication.instance()
    #         if app is not None:
    #             app.removeEventFilter(self)

    def _start_drag(self, global_pos):
        self._drag_global_start = global_pos
        self._dragging = True
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        # 不再需要 scroll_area 引用

    def _stop_drag(self):
        if self._dragging:
            self._dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def eventFilter(self, watched, event):
        """Global event filter: handles mouse move and release during dragging."""
        if not self._dragging:
            return super().eventFilter(watched, event)

        # Use QEvent.Type enum to eliminate IDE warning on MouseMove
        if event.type() == QEvent.Type.MouseMove:
            mouse_event = cast(QMouseEvent, event)
            # Calculate movement delta and adjust scroll bars accordingly
            global_pos = mouse_event.globalPosition().toPoint()
            delta = global_pos - self._drag_global_start
            self.drag_offset.emit(delta.x(), delta.y())  # 发出信号
            self._drag_global_start = global_pos  # 更新起点，实现相对移动
            return True   # Event handled

        # Use QEvent.Type.MouseButtonRelease
        elif event.type() == QEvent.Type.MouseButtonRelease:
            # Cast event to QMouseEvent to safely access button()
            mouse_event = cast(QMouseEvent, event)
            if mouse_event.button() == Qt.MouseButton.LeftButton:
                self._stop_drag()
                return True

        return super().eventFilter(watched, event)

    # ---------- Mouse events (entry points for drag) ----------
    def mousePressEvent(self, event: QMouseEvent):
        """Start dragging when the left button is pressed (only if a scroll area exists)."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_drag(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """If the mouse button is released inside the widgets, stop dragging."""
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._stop_drag()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    # ---------- Zoom, load, paint (unchanged core logic) ----------
    def load_pixmap(self, pixmap: QPixmap):
        """Load a new pixmap, reset zoom to 100%, and resize the widgets."""
        self._pixmap = pixmap
        self._zoom_factor = 1.0
        if not pixmap.isNull():
            self.resize(pixmap.size())
        else:
            self.resize(0, 0)
        self.update()

    def pixmap(self) -> QPixmap:
        """Return the currently displayed pixmap."""
        return self._pixmap

    def zoom_factor(self) -> float:
        """Return the current zoom factor."""
        return self._zoom_factor

    def set_zoom_factor(self, factor: float):
        """Apply a new zoom factor, clamped to allowed range.
        Resizes the widgets and triggers a repaint."""
        if self._pixmap.isNull():
            return
        factor = max(self.MIN_ZOOM, min(self.MAX_ZOOM, factor))
        if abs(factor - self._zoom_factor) < 1e-6:
            return
        self._zoom_factor = factor
        # Update widgets size to reflect the zoomed image dimensions
        new_size = (self._pixmap.size().toSizeF() * self._zoom_factor).toSize()
        self.resize(new_size)
        self.update()

    def zoom_in(self, step: float = ZOOM_STEP):
        """Increase zoom by the given step."""
        self.set_zoom_factor(self._zoom_factor + step)

    def zoom_out(self, step: float = ZOOM_STEP):
        """Decrease zoom by the given step."""
        self.set_zoom_factor(self._zoom_factor - step)

    def paintEvent(self, event):
        """Draw the pixmap scaled by the current zoom factor."""
        painter = QPainter(self)
        if not self._pixmap.isNull():
            # Use QPainter.RenderHint enum for clarity
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            # Scale the painter so the pixmap is drawn at the zoomed size
            painter.scale(self._zoom_factor, self._zoom_factor)
            painter.drawPixmap(0, 0, self._pixmap)

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel events: zoom in/out when Ctrl is held."""
        # Use KeyboardModifier enum for ControlModifier
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    class MainWindow(QMainWindow):
        """Main application window with a menu and a scrollable image viewer."""

        def __init__(self):
            super().__init__()
            self.setWindowTitle("Image Viewer - Zoom changes widgets size")
            self.resize(800, 600)

            # Scroll area that will contain the image viewer
            self.scroll_area = QScrollArea()
            self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Disable automatic widgets resizing so the viewer keeps its natural size
            self.scroll_area.setWidgetResizable(False)

            # Image viewer widgets
            self.image_viewer = ImageViewer()
            self.scroll_area.setWidget(self.image_viewer)
            self.image_viewer.set_scroll_area(self.scroll_area)

            self.setCentralWidget(self.scroll_area)

            # Simple menu bar
            menubar = self.menuBar()
            file_menu = menubar.addMenu("File")
            open_action = file_menu.addAction("Open")
            open_action.triggered.connect(self.open_image)

        def open_image(self):
            """Open a file dialog and load the selected image."""
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
            )
            if file_path:
                pixmap = QPixmap(file_path)
                if pixmap.isNull():
                    print("Cannot load image:", file_path)
                    return
                self.image_viewer.load_pixmap(pixmap)
                # Optionally resize window to fit the image (within screen limits)
                self.adjust_window_to_image()

        def adjust_window_to_image(self):
            """Resize the window to fit the current zoomed image,
            but not larger than the available screen area."""
            viewer = self.image_viewer
            if viewer.pixmap().isNull():
                return
            # Desired size = viewer size + extra space for scroll bars and window decoration
            desired = viewer.size()
            extra_w = self.width() - self.scroll_area.viewport().width()
            extra_h = self.height() - self.scroll_area.viewport().height()
            win_w = desired.width() + extra_w
            win_h = desired.height() + extra_h

            # Clamp to screen available geometry
            screen = QApplication.primaryScreen().availableGeometry()
            win_w = min(win_w, screen.width())
            win_h = min(win_h, screen.height())
            self.resize(win_w, win_h)


    app_ = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app_.exec())
