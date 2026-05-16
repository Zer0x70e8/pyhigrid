#
""""""

from typing import Callable


def log(msg, log_func: Callable):
    def log_decorator(func):
        def wrapper(*args, **kwargs):
            return (
                func(*args, **kwargs),
                log_func(msg)
            )[0]
        return wrapper
    return log_decorator
