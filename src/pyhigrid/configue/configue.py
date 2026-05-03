#
"""Configuration Unified Engine"""

from itertools import chain

from .utils.namespace import Namespace, FrozenNamespace


class Configue:
    __slots__ = ("static", "dynamic", "_logger")

    def __init__(self):
        self.static = StaticConfig()
        self.dynamic = DynamicConfig()
        self._logger = None

    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, logger):
        self._logger = logger
        self.dynamic.logger = logger

    def check(self):
        if self._logger is None:
            raise RuntimeError("Configurator missing logging function.")

    def __str__(self):
        return "\n".join((
            f"{type(self).__name__}",
            f"\t{type(self.static).__name__}: (",
            *chain.from_iterable(
                [f"\t\t{k}: {v}"] if not isinstance(v, Namespace)
                else [f"\t\t{k}:"] + [f"\t\t\t{k_}: {v_}" for k_, v_ in v.items()]
                for k, v in self.static.items()
            ),
            "\t\t)",
            f"\t{type(self.dynamic).__name__}: (",
            *chain.from_iterable(
                [f"\t\t{k}: {v}"] if not isinstance(v, Namespace)
                else [f"\t\t{k}:"] + [f"\t\t\t{k_}: {v_}" for k_, v_ in v.items()]
                for k, v in self.dynamic.items()
            ),
            "\t\t)",
        ))


class StaticConfig(FrozenNamespace):
    """Immutable configuration carrier loaded from a nested dictionary.

    Inherits from FrozenNamespace to provide a read-once, read-many container.
    """

    def __init__(self, **entries):
        # Initialize as unfrozen so that load() can write attributes.
        super().__init__(**entries)

    def load(self, config_dict: dict):
        """Load configuration from a doubly-nested dictionary.

        Keys become attributes; sub-dictionaries become nested FrozenNamespace
        instances. Once loaded, the instance is frozen and further attempts to
        modify it (including calling load again) will raise an AttributeError.
        """
        # FrozenNamespace raises AttributeError if already frozen,
        # so trying to set an attribute here acts as the "already loaded" guard.
        for key, value in config_dict.items():
            # Attribute setting will convert any dict value to a nested
            # FrozenNamespace automatically (via Namespace.__setattr__).
            setattr(self, key, value)

        # Seal the namespace – no more changes allowed.
        self.frozen()

    def __str__(self):
        return f"{type(self).__name__}\n" + ("\t\n".join(
            f"{k}: {v}" for k, v in self.items()
        ))


class DynamicConfig(Namespace):
    """"""

    def __init__(self, **entries):
        super().__init__(**entries)
        self._logger = None

    def __str__(self):
        return f"{type(self).__name__}\n" + ("\t\n".join(
            f"{k}: {v}" for k, v in self.items()
        ))

    def items(self):
        results = {}
        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue
            results[k] = v
        return results
