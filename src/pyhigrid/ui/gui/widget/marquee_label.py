"""
Pixel-smooth scrolling marquee with customizable spacing between text copies
(fixed pixels or relative to component width). Supports pause interval before each scroll cycle.
"""

from typing import overload
from PyQt6.QtWidgets import QLabel, QApplication, QWidget
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFontMetrics, QPainter, QFontDatabase


class MarqueeLabel(QLabel):
    """Pixel-smooth scrolling marquee with configurable gap between text copies.
    Pause occurs before each scrolling cycle.
    """

    @overload
    def __init__(self, parent=None):
        ...

    @overload
    def __init__(self, text: str = "", parent=None):
        ...

    def __init__(self, arg1: str | QWidget = None, arg2=None):
        if isinstance(arg1, str):
            super().__init__(arg1, arg2)
            text = arg1
        else:
            super().__init__(arg1)
            text = ""

        # Set default monospaced font
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        if fixed_font:
            self.setFont(fixed_font)

        self.full_text = text          # Original text without extra placeholders
        self.offset = 0                # Scroll offset in pixels
        self.timer: QTimer = QTimer(self)
        self.timer.timeout.connect(self._scroll)
        self._is_scrolling = False
        self._text_width = 0            # Cached total text width
        self._step = 1                  # Pixels moved per timer tick
        self._interval = 30             # Timer interval in milliseconds

        # Pause interval before each scroll cycle
        self._pause_interval_ms = 1000  # Default pause 1 second
        self._pending_start_timer = None  # Timer for delayed start

        # Gap between text copies (pixels)
        self._spacing_px = 0            # Actual gap in pixels
        self._spacing_ratio = 0.0       # Gap as ratio of widget width (0~1), higher priority than fixed pixels

        # DPI scaling factor
        self._dpi_factor = self._get_dpi_factor()

        self.setWordWrap(False)         # No wrapping for marquee
        self.setText(text)

    # Public API
    # noinspection PyPep8Naming
    def setPauseInterval(self, ms: int):
        """Set pause interval (ms) before each scroll cycle. Set 0 to disable pause."""
        self._pause_interval_ms = max(0, ms)

    # noinspection PyPep8Naming
    def setSpacingPixels(self, pixels: int):
        """Set fixed gap between text copies in pixels."""
        self._spacing_ratio = 0.0
        self._spacing_px = max(0, pixels)
        self._update_scroll_state()

    # noinspection PyPep8Naming
    def setSpacingRatio(self, ratio: float):
        """
        Set gap between text copies as a ratio of widget width (0~1).
        E.g., ratio=0.2 means gap = 20% of widget width.
        """
        self._spacing_ratio = max(0.0, min(1.0, ratio))
        self._update_spacing_from_ratio()
        self._update_scroll_state()

    def setText(self, text: str):
        """Override setText to update cache and re-evaluate scroll requirements."""
        self._cancel_pending_start()
        self.full_text = text
        self.offset = 0
        self._update_text_width()
        super().setText(text)
        self._update_scroll_state()
        self.update()

    # Internal Logic
    @staticmethod
    def _get_dpi_factor():
        """Return DPI scaling factor based on 96 DPI baseline."""
        screen = QApplication.primaryScreen()
        if screen:
            dpi = screen.logicalDotsPerInch()
            return dpi / 96.0
        return 1.0

    def _update_spacing_from_ratio(self):
        """Calculate actual pixel gap from ratio and current widget width."""
        if self._spacing_ratio > 0:
            width = self.contentsRect().width()
            self._spacing_px = int(width * self._spacing_ratio)

    def _update_text_width(self):
        """Compute pixel width of full text using current font."""
        if not self.full_text:
            self._text_width = 0
            return
        fm = QFontMetrics(self.font())
        self._text_width = fm.horizontalAdvance(self.full_text)

    def _update_scroll_state(self):
        """Determine whether scrolling is needed based on text and widget width."""
        if self._spacing_ratio > 0:
            self._update_spacing_from_ratio()

        available_width = self.contentsRect().width()
        need_scroll = self._text_width > available_width

        if not need_scroll:
            self._stop_scroll()
            self._cancel_pending_start()
            self.offset = 0
            self.update()
            return

        # Scrolling needed and not already scrolling or waiting -> start with delay
        if not self._is_scrolling and self._pending_start_timer is None:
            self._start_scroll_with_delay()

    def _start_scroll_with_delay(self):
        """Start scrolling after the configured pause interval, or immediately if pause is zero."""
        if self._pause_interval_ms > 0:
            self._stop_scroll()
            self._cancel_pending_start()
            self._pending_start_timer: QTimer = QTimer(self)
            self._pending_start_timer.setSingleShot(True)
            self._pending_start_timer.timeout.connect(self._start_scroll_now)
            self._pending_start_timer.start(self._pause_interval_ms)
        else:
            self._start_scroll_now()

    def _start_scroll_now(self):
        """Immediately start scrolling: reset offset, compute parameters, start timer."""
        self._cancel_pending_start()
        self.offset = 0
        self.update()
        self._calculate_scroll_params()
        self._is_scrolling = True
        self.timer.setInterval(self._interval)
        self.timer.start()

    def _stop_scroll(self):
        """Stop the scrolling timer."""
        if self._is_scrolling:
            self.timer.stop()
            self._is_scrolling = False

    def _cancel_pending_start(self):
        """Cancel any pending delayed start timer."""
        if self._pending_start_timer is not None:
            self._pending_start_timer.stop()
            self._pending_start_timer.deleteLater()
            self._pending_start_timer = None

    def _scroll(self):
        """Update offset and trigger repaint; when end is reached, prepare next cycle."""
        if not self.full_text:
            return

        self.offset += self._step
        total_scroll_distance = self._text_width + self._spacing_px

        if self.offset >= total_scroll_distance:
            # End of scroll: stop, reset, and schedule next cycle (with pause)
            self._stop_scroll()
            self.offset = 0
            self.update()
            self._start_scroll_with_delay()
        else:
            self.update()

    def _calculate_scroll_params(self):
        """Compute scroll step and timer interval based on DPI scaling."""
        self._dpi_factor = self._get_dpi_factor()
        base_speed_px_per_sec = 50.0
        speed_px_per_sec = base_speed_px_per_sec * self._dpi_factor
        step = 1
        interval_ms = (step / speed_px_per_sec) * 1000
        interval_ms = max(10, min(int(interval_ms), 50))
        self._step = step
        self._interval = int(interval_ms)

    # Painting & Events
    def paintEvent(self, event):
        available_width = self.contentsRect().width()
        if self._text_width <= available_width:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setFont(self.font())
        painter.setPen(self.palette().windowText().color())

        rect = self.contentsRect()
        fm = painter.fontMetrics()
        text_height = fm.height()
        y = rect.y() + (rect.height() - text_height) // 2 + fm.ascent()
        painter.setClipRect(rect)

        # First text copy starting X
        x1 = rect.x() - self.offset
        painter.drawText(x1, y, self.full_text)

        # Determine if second copy (with gap) is needed
        remaining_width = rect.width() - (self._text_width - self.offset)
        if remaining_width > 0:
            x2 = x1 + self._text_width + self._spacing_px
            painter.drawText(x2, y, self.full_text)

        painter.end()

    def resizeEvent(self, event):
        """Re-evaluate scroll state when widget is resized, cancel pending start."""
        self._cancel_pending_start()
        super().resizeEvent(event)
        self._update_text_width()
        self._update_scroll_state()
        total = self._text_width + self._spacing_px
        if 0 < total <= self.offset:
            self.offset = 0