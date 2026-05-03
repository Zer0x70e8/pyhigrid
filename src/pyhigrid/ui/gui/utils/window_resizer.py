#
"""Self-implemented window resizing functionality"""

from PySide6.QtGui import QMouseEvent, QCursor
from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtWidgets import QWidget, QApplication, QAbstractButton, QSlider, QComboBox

__all__ = ["WindowResizer", "Direction"]


class Direction:
    """Bit flags for resize directions. Combine using | operator."""
    NONE = 0
    UP = 1  # 0001
    DOWN = 2  # 0010
    LEFT = 4  # 0100
    RIGHT = 8  # 1000
    TOP_LEFT = UP | LEFT
    TOP_RIGHT = UP | RIGHT
    BOTTOM_LEFT = DOWN | LEFT
    BOTTOM_RIGHT = DOWN | RIGHT

    @staticmethod
    def from_mouse_pos(x: int, y: int,
                       w: int, h: int,
                       margin: int) -> int:
        """
        Determine resize direction from local mouse position.

        Algorithm:
        - If x within left margin -> add LEFT flag.
        - If x within right margin -> add RIGHT flag.
        - If y within top margin -> add UP flag.
        - If y within bottom margin -> add DOWN flag.
        Returns a combination of flags (bitwise OR).
        """
        dir_flag = 0
        if x <= margin:
            dir_flag |= Direction.LEFT
        if x >= w - margin:
            dir_flag |= Direction.RIGHT
        if y <= margin:
            dir_flag |= Direction.UP
        if y >= h - margin:
            dir_flag |= Direction.DOWN
        return dir_flag


class WindowResizer(QObject):
    """
    Adds frameless window resizing and dragging.

    How it works:
    - Listens to global mouse events via event filter.
    - When mouse is near window edges, changes cursor shape.
    - On left button press, starts dragging/resizing.
    - During drag, updates window geometry accordingly.
    - Dragging (moving) is only allowed when clicking on the title bar area.
    - Special handling: if window is maximized, a click on the title bar restores it and
      moves it under the mouse cursor before starting drag.
    """

    def __init__(self, parent: QWidget = None,
                 window_: QWidget = None,
                 setup_flag: bool = True):
        super().__init__(parent)
        self.window_ = window_
        self._margin = 8  # Edge thickness for resizing
        self._title_bar_height = 30  # Height of the draggable title bar area

        self.drag_start_pos = None  # Global mouse pos at drag start
        self.drag_start_geometry = None  # Window geometry at drag start
        self.is_dragging = False
        self.last_direction: Direction | int = Direction.TOP_LEFT

        if window_ is not None:
            self.install(window_, setup_flag)

    @property
    def margin(self):
        return self._margin

    @margin.setter
    def margin(self, value: int):
        self._margin = value

    @property
    def title_bar_height(self):
        return self._title_bar_height

    @title_bar_height.setter
    def title_bar_height(self, value: int):
        self._title_bar_height = value

    def install(self, window_: QWidget, setup_flag: bool = True):
        """Attach resizer to a window. If setup_flag is True, makes window frameless."""
        self.window_ = window_
        # Install filter globally to capture events even when mouse is over child widgets
        QApplication.instance().installEventFilter(self)
        if not setup_flag:
            return
        window_.setMouseTracking(True)
        window_.setWindowFlag(Qt.WindowType.FramelessWindowHint)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Handle mouse events for resizing and dragging."""
        if event.type() not in (QEvent.Type.MouseMove,
                                QEvent.Type.MouseButtonPress,
                                QEvent.Type.MouseButtonRelease):
            return super().eventFilter(watched, event)

        # For all mouse events, check whether they belong to the target window.
        if isinstance(watched, QWidget):
            top_level = watched.window()
            if top_level is not self.window_:
                return super().eventFilter(watched, event)
        else:
            return super().eventFilter(watched, event)

        # Type hint: event is actually a QMouseEvent for
        #   the event types we filter (MouseMove, MouseButtonPress, MouseButtonRelease)
        event: QMouseEvent

        match event.type():
            case QEvent.Type.MouseMove:
                if self.window_.isMaximized():
                    self.window_.unsetCursor()
                    return False
                if not self.is_dragging:
                    # Update cursor shape based on edge proximity
                    direction = self.get_direction(event)
                    self.change_mouse(direction)
                    self.last_direction = direction
                    return False

                # Dragging in progress: move or resize window
                current_global = event.globalPosition().toPoint()
                delta = current_global - self.drag_start_pos
                geo = self.drag_start_geometry
                dir_flag = self.last_direction

                # No edge -> drag the whole window
                if dir_flag == Direction.NONE:
                    self.window_.windowHandle().startSystemMove()
                    # self.window_.move(
                    #     geo.x() + delta.x(), geo.y() + delta.y())
                    return True

                # Resize logic: start from saved geometry, apply delta to edges
                x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
                dx, dy = delta.x(), delta.y()

                if dir_flag & Direction.LEFT:
                    x = geo.x() + dx
                    w = geo.width() - dx
                if dir_flag & Direction.RIGHT:
                    w = geo.width() + dx
                if dir_flag & Direction.UP:
                    y = geo.y() + dy
                    h = geo.height() - dy
                if dir_flag & Direction.DOWN:
                    h = geo.height() + dy

                old_w, old_h = w, h

                # Clamp to min/max size
                w = max(self.window_.minimumWidth(),
                        min(self.window_.maximumWidth(), w))
                h = max(self.window_.minimumHeight(),
                        min(self.window_.maximumHeight(), h))

                # Compensation: if width/height was clamped and resizing from left/top -> shift position.
                if w != old_w and (dir_flag & Direction.LEFT):
                    x -= (w - old_w)
                if h != old_h and (dir_flag & Direction.UP):
                    y -= (h - old_h)

                self.window_.setGeometry(x, y, w, h)
                return False

            case QEvent.Type.MouseButtonPress:
                local_pos = self.window_.mapFromGlobal(event.globalPosition().toPoint())
                # If the mouse clicks on a button-type control, do not interfere.
                child = self.window_.childAt(local_pos)
                # print(f"Clicked widget: {child}, is button: {isinstance(child, QAbstractButton)}")
                if child is not None and isinstance(child, QAbstractButton):
                    return super().eventFilter(watched, event)

                # Get resize direction from mouse position
                direction = self.get_direction(event)

                # Maximized window handling: only allow drag from title bar
                if self.window_.isMaximized():
                    # 重要：再次检查是否点击在按钮上（防止 childAt 失败或被覆盖）
                    if child is not None and isinstance(child, (QAbstractButton, QSlider, QComboBox)):
                        return False
                    if local_pos.y() <= self._title_bar_height:
                        global_pos = event.globalPosition().toPoint()
                        screen = self.window_.screen()
                        screen_width = screen.geometry().width() if screen else 1920

                        # Ratio of mouse X within maximized window.
                        ratio = local_pos.x() / screen_width if screen_width > 0 else 0

                        self.window_.showNormal()

                        # Compute new position: keep same relative X offset from left,
                        # and place top near mouse Y minus margins.
                        normal_width = self.window_.width()
                        new_x = global_pos.x() - int(normal_width * ratio)
                        new_y = global_pos.y() - self._margin - int(self._title_bar_height / 2)
                        self.window_.move(new_x, new_y)

                        # Update drag start state after move
                        self.drag_start_geometry = self.window_.geometry()
                        self.drag_start_pos = event.globalPosition().toPoint()
                        self.last_direction = Direction.NONE
                        self.is_dragging = True
                        return True
                    else:
                        # Click outside title bar when maximized: ignore
                        return super().eventFilter(watched, event)

                # Normal (non-maximized) window
                # Resize takes precedence over drag
                if direction != Direction.NONE:
                    # Start resizing
                    self.drag_start_pos = event.globalPosition().toPoint()
                    self.drag_start_geometry = self.window_.geometry()
                    self.last_direction = direction
                    self.is_dragging = True
                    return True
                elif local_pos.y() <= self._title_bar_height:
                    # Start dragging (moving) only if in title bar area
                    self.drag_start_pos = event.globalPosition().toPoint()
                    self.drag_start_geometry = self.window_.geometry()
                    self.last_direction = Direction.NONE
                    self.is_dragging = True
                    return True
                else:
                    # Click in content area, not on edge or title bar: ignore
                    return super().eventFilter(watched, event)

            case QEvent.Type.MouseButtonRelease:
                self.is_dragging = False
                if self.get_direction(event) == Direction.NONE:
                    self.window_.unsetCursor()
                return False

        return super().eventFilter(watched, event)

    def change_mouse(self, direction: Direction | int) -> None:
        """Update cursor shape based on resize direction. Skips if same as last."""
        if direction == self.last_direction:
            return
        match direction:
            case Direction.UP | Direction.DOWN:
                self.set_cursor(Qt.CursorShape.SizeVerCursor)
            case Direction.LEFT | Direction.RIGHT:
                self.set_cursor(Qt.CursorShape.SizeHorCursor)
            case Direction.TOP_LEFT | Direction.BOTTOM_RIGHT:
                self.set_cursor(Qt.CursorShape.SizeFDiagCursor)
            case Direction.BOTTOM_LEFT | Direction.TOP_RIGHT:
                self.set_cursor(Qt.CursorShape.SizeBDiagCursor)
            case Direction.NONE:
                self.window_.unsetCursor()

    def get_direction(self, event: QMouseEvent) -> int:
        """Get resize direction flags from mouse position relative to window."""
        pos = self.window_.mapFromGlobal(event.globalPosition().toPoint())
        return Direction.from_mouse_pos(
            pos.x(), pos.y(),
            self.window_.width(),
            self.window_.height(),
            self.margin
        )

    def set_cursor(self, shape):
        """Helper to set window cursor."""
        self.window_.setCursor(QCursor(shape))
