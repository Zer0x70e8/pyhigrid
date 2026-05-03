#
"""A simple observable value with optional validation and error handling."""

__all__ = ['ObservableValue']  # This looks superfluous.


class ObservableValue:
    """A value container that notifies registered callbacks on changes.

    This class implements a basic observer pattern.  Whenever ``set()`` is
    called and the value actually changes, all registered callbacks are invoked
    with the new and old values.  Validation and error handling are pluggable
    through constructor arguments.

    Attributes:
        _value: The currently stored value.
        _callbacks: List of registered callback functions.
        _validator: Optional callable used to validate/transform new values.
        _on_error: Optional callable invoked when a callback raises an exception.
    """

    def __init__(self, initial_value, validator=None, on_error=None):
        """Initialize the observable value.

        Args:
            initial_value: The initial value to store.
            validator: A callable that receives the new value and must return
                the (possibly transformed) value.  If the value is invalid the
                callable should raise an exception.  **If ``None`` (the
                default), no validation is performed** and the value is
                accepted as-is.
            on_error: A callable that will be called when a registered callback
                raises an exception.  The callable receives the exception
                object as its only argument.  **If ``None`` (the default),
                callback exceptions are silently ignored** (the original
                behaviour).  Set this to a logging function, a custom error
                handler, or ``raise`` to propagate the first exception.
        """
        self._value = initial_value
        self._callbacks = []
        self._validator = validator
        self._on_error = on_error

    def get(self):
        """Return the current value.

        Returns:
            The stored value.
        """
        return self._value

    def set(self, new_value):
        """Update the stored value and notify all callbacks.

        Validation / transformation:
            If a *validator* was supplied during construction, it is called
            with *new_value* and the result is used as the actual stored value.
            The validator may raise an exception to reject the update.

        Callback invocation:
            All registered callbacks are invoked in the order they were
            registered.  Each callback receives two positional arguments:
            ``callback(new_value, old_value)``.

            If a callback raises an exception, the behaviour depends on the
            *on_error* handler passed to the constructor:

            * If *on_error* is ``None`` (the default), the exception is
              **silently ignored** and the remaining callbacks are still
              executed.
            * If *on_error* is a callable, it is invoked with the exception
              object as its argument.  After it returns, the next callback is
              processed.  The callable can choose to log the error, collect it,
              or re-raise it (which will stop the notification loop).

        Args:
            new_value: The value to store (after optional validation).
        """
        if self._validator is not None:
            new_value = self._validator(new_value)

        old = self._value
        self._value = new_value

        for callback in self._callbacks:
            try:
                callback(new_value, old)
            except Exception as e:
                if self._on_error is not None:
                    self._on_error(e)

    def on_change(self, callback):
        """Register a callback to be invoked on every value change.

        The callback must accept two arguments: the new value and the old
        value.

        Args:
            callback: A callable ``f(new_value, old_value)``.

        Returns:
            A function that, when called, unregisters *callback* so that it
            will no longer receive notifications.  The returned function can
            be called multiple times safely; subsequent calls have no effect.
        """
        self._callbacks.append(callback)

        def unsubscribe():
            if callback in self._callbacks:
                self._callbacks.remove(callback)

        return unsubscribe
