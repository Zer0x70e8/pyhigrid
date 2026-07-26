#
""""""

class BoolLatch:
    """A lightweight boolean latch state machine for UI overlay switching.

    Offers both a toggle operation (logical NOT) and a direct set method.
    Change callbacks make it easy to bind to any UI framework.
    """

    def __init__(self, initial: bool = False):
        """Initialize the latch.

        Args:
            initial: Starting state of the latch (default: False / off).
        """
        self._state = initial
        self._callbacks: list = []  # Registered state-change listeners

    @property
    def state(self) -> bool:
        """The current latched value (True/False)."""
        return self._state

    def toggle(self) -> bool:
        """Flip the state (logical NOT) and notify listeners.

        Returns:
            The new state after toggling.
        """
        self._state = not self._state
        self._notify()
        return self._state

    def set(self, value: bool) -> bool:
        """Force the latch to a specific state.

        If the new value is the same as the current state, no notification is sent.
        This avoids unnecessary UI redraws.

        Args:
            value: The desired state (truthy/falsy, coerced to bool).

        Returns:
            The new state after setting.
        """
        value = bool(value)
        if self._state != value:
            self._state = value
            self._notify()
        return self._state

    def on_change(self, callback) -> None:
        """Register a function to be called whenever the state changes.

        The callback must accept a single argument: the new state (bool).
        Multiple callbacks can be registered; they are called in order of registration.

        Args:
            callback: A callable that receives the new state.
        """
        self._callbacks.append(callback)

    def _notify(self) -> None:
        """Invoke all registered callbacks with the current state.

        Callback exceptions are silently swallowed to keep the toggle/set
        operations robust in UI contexts.
        """
        for cb in self._callbacks:
            try:
                cb(self._state)
            except Exception:
                pass  # UI callbacks should never break the state machine


if __name__ == "__main__":
    overlay_switch = BoolLatch(False)

    # Bind a UI update function
    overlay_switch.on_change(lambda on: print(f"Overlay {'shown' if on else 'hidden'}"))

    overlay_switch.toggle()  # -> Overlay shown
    overlay_switch.set(False)  # -> Overlay hidden
