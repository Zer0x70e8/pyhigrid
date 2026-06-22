#
""""""

import traceback
import logging
from typing import Any, Callable, Dict, Tuple, List


class Container:
    logger = logging.getLogger("pyhigrid.container")

    def __init__(self):
        self._factories: Dict[str, Tuple[Callable[[], Any], bool]] = {}
        self._instances: Dict[str, Any] = {}
        self._boot_callbacks: List[Callable[[], Any]] = []

        # alias
        self.reg = self.register
        self.on = self.on_boot

    def register(self, name: str, factory: Callable[[], Any], singleton=True):
        # assert (not isinstance(factory, function)), traceback.print_stack()
        self._factories[name] = (factory, singleton)
        # import traceback
        # traceback.print_stack()

    def get(self, name: str):
        if name in self._instances:
            return self._instances[name]
        factory, singleton = self._factories[name]
        instance = factory()
        if singleton:
            self._instances[name] = instance
        return instance

    def on_boot(self, callback: Callable[[], Any]) -> None:
        self._boot_callbacks.append(callback)

    def on_boot_insert(self, index: int, callback: Callable[[], Any]) -> None:
        self._boot_callbacks.insert(index, callback)

    def exec(self):
        for callback in self._boot_callbacks:
            # noinspection PyBroadException
            try:
                callback()
            except RuntimeError:
                raise
            except Exception:
                # 记录日志或做其他处理
                self.logger.error(
                    f"Boot callback error: "
                    f"{traceback.format_exc()}"
                )
