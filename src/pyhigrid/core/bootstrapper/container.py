#
""""""

from typing import Any, Callable, Dict, Tuple


class Container:
    def __init__(self):
        self._factories: Dict[str, Tuple[Callable[[], Any], bool]] = {}
        self._instances: Dict[str, Any] = {}

    def register(self, name: str, factory: Callable[[], Any], singleton=True):
        self._factories[name] = (factory, singleton)

    def get(self, name: str):
        if name in self._instances:
            return self._instances[name]
        factory, singleton = self._factories[name]
        instance = factory()
        if singleton:
            self._instances[name] = instance
        return instance
