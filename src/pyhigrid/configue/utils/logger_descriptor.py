#
""""""
import logging
from typing import Optional, Union, Callable


class LoggerDescriptor:
    """描述符：为所在实例管理 _logger 的懒创建。"""

    def __init__(self, default_factory=None):
        # default_factory 仅用于 Configue；DynamicConfig 会覆盖 get 行为
        self.default_factory = default_factory

    def __set_name__(self, owner, name):
        self.storage_name = f"_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self
        try:
            return getattr(instance, self.storage_name)
        except AttributeError:
            pass
        if self.default_factory:
            value = self.default_factory()
            setattr(instance, self.storage_name, value)
            return value
        raise AttributeError(f"{owner.__name__} logger not set.")

    def __set__(self, instance, value):
        setattr(instance, self.storage_name, value)


class LazyLogger:
    """描述符：为宿主类的实例（或类本身）提供懒加载的 Logger 对象。

    参数:
        name: 日志器名称。
              - 字符串: 直接作为 logger 名称。
              - 可调用对象: 接受宿主实例作为参数，返回字符串名称。
              - 默认 None: 使用宿主类的全限定名 (module.ClassName)。
        level: 日志级别，仅在首次创建 logger 时设置。默认为 logging.DEBUG。
    """

    def __init__(
        self,
        name: Optional[Union[str, Callable[[object], str]]] = None,
    ):
        self._name_source = name
        self._attr_name: Optional[str] = None          # 由 __set_name__ 设置

    def __set_name__(self, owner: type, name: str) -> None:
        """自动获取描述符在类中被赋予的属性名。"""
        self._attr_name = name

    def __get__(self, instance: Optional[object], owner: type) -> logging.Logger:
        # 1. 如果通过类访问（instance is None），直接返回全局 logger。
        #    logging.getLogger 本身是单例，无需额外缓存。
        if instance is None:
            return self._create_logger(owner)

        # 2. 实例访问：优先从实例字典中取缓存
        cache_key = self._attr_name
        if cache_key is None:
            raise RuntimeError("描述符未通过 __set_name__ 绑定属性名")

        # 如果实例字典中没有，则创建并存入实例属性（屏蔽描述符后续调用）
        if cache_key not in instance.__dict__:
            logger = self._create_logger(owner, instance)
            instance.__dict__[cache_key] = logger   # 缓存到实例
        return instance.__dict__[cache_key]

    def _create_logger(
        self, owner: type, instance: Optional[object] = None
    ) -> logging.Logger:
        """根据配置生成 logger 并设置级别。"""
        # 确定 logger 名称
        name = self._resolve_name(owner, instance)
        logger = logging.getLogger(name)
        return logger

    def _resolve_name(
        self, owner: type, instance: Optional[object]
    ) -> str:
        """解析最终的 logger 名称。"""
        if self._name_source is None:
            # 默认使用类的全限定名
            return f"{owner.__module__}.{owner.__qualname__}"
        if callable(self._name_source):
            # 可调用对象应接受实例（类访问时 instance 为 None）
            return self._name_source(instance)
        # 普通字符串
        return self._name_source
