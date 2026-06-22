#
""""""

import logging
import sys
from typing import Optional, List, Dict, Any

from pyhigrid.core.build_logger import TRACE

class EarlyLogger:
    """早期日志器：缓冲日志，待正式日志就绪后重放或直通。"""

    def __init__(self, name: str = "config_early", *, buffer_limit: Optional[int] = None):
        self.name = name
        # 内部维护一个缓冲区
        self._buffer: List[Dict[str, Any]] = []
        # 可选的环形缓冲（buffer_limit 为 None 时无上限）
        self._buffer_limit = buffer_limit
        # 正式 logger，为 None 时代表尚未就绪
        self._official: Optional[logging.Logger] = None
        # 立即输出到 stderr 的回退（调试用，可选）
        self._fallback = logging.StreamHandler(sys.stderr)
        self._fallback.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    def _log(self, level: int, msg: str, *args, **kwargs):
        record = {"level": level, "msg": msg, "args": args, "kwargs": kwargs}
        if self._official is not None:
            # 已绑定正式 logger，直接输出
            self._official.log(level, msg, *args, **kwargs)
            return

        # 缓冲阶段：先存入 buffer
        if self._buffer_limit is None or len(self._buffer) < self._buffer_limit:
            self._buffer.append(record)
        # 同时可选地 fallback 到 stderr，方便调试
        # self._fallback.emit(logging.makeLogRecord(record))

    def trace(self, msg, *args, **kwargs):
        """记录 TRACE 级别日志（比 DEBUG 更详细）。"""
        self._log(TRACE, msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self._log(logging.CRITICAL, msg, *args, **kwargs)

    def flush_to(self, logger: logging.Logger):
        """将所有缓冲日志重放到正式 logger，并清空缓冲。"""
        for rec in self._buffer:
            logger.log(rec["level"], rec["msg"], *rec["args"], **rec["kwargs"])
        self._buffer.clear()

    def attach(self, logger: logging.Logger):
        """切换到正式 logger：后续日志直接输出，不再缓冲。"""
        self._official = logger
        # 这里也可以立刻 flush 一次，确保缓冲的历史也进入正式日志
        self.flush_to(logger)
