#
""""""

import logging
import threading
from typing import List, Callable, Any, Dict

from albuswall.repositories import IngestSourceRepository
from albuswall.domain.types import (
    ScheduledTriggerConfig,
    DeviceTriggerConfig,
    SourceMeta,
    ScheduledTriggerTuple,
    DeviceTriggerTuple,
)

from .trigger_scheduler import SchedulerWorker


class TriggerService:
    _logger: logging.Logger = logging.getLogger(__name__)
    _source_repo: IngestSourceRepository

    def __init__(self, repo: IngestSourceRepository):
        self._source_repo = repo

        # 触发器列表：只保存 (SourceMeta, Config)
        self._scheduled_triggers: List[ScheduledTriggerTuple] = []
        self._device_triggers: List[DeviceTriggerTuple] = []

        # 回调字典：source_id -> List[Callable]
        self._scheduled_callbacks: Dict[str, List[Callable]] = {}
        self._device_callbacks: Dict[str, List[Callable]] = {}

        self._lock = threading.Lock()

        # 创建调度 worker，并注入回调执行方法
        self._worker = SchedulerWorker(self._execute_scheduled_callbacks)

        # 初始加载触发器，并同步到调度器
        self.update_triggers()

    def start(self) -> None:
        """启动调度服务。"""
        self._worker.start()

    def stop(self) -> None:
        """停止调度服务。"""
        self._worker.stop()

    def update_triggers(self) -> None:
        """从数据仓库重新加载所有触发器，完全替换现有列表，并同步到调度器。

        note：此操作不会清理已注册的回调，若需清理孤儿回调请调用 clean_orphan_callbacks()。
        """
        with self._lock:
            # 清空旧触发器列表
            self._scheduled_triggers.clear()
            self._device_triggers.clear()

            sources = self._source_repo.get_all()
            for src in sources:
                # 直接使用实体属性，不再依赖 trigger_config 字典
                if not src.scheduled_enabled and not src.device_trigger_enabled:
                    continue

                meta: SourceMeta = {
                    "source_id": str(src.id),
                    "title": src.title or "",
                    "source_path": src.source_path or "",
                }

                # 检查计划触发器
                if src.scheduled_enabled:
                    scheduled_cfg: ScheduledTriggerConfig = {
                        "scheduled_enabled": True,
                        "update_mode": src.update_mode or "",
                        "scheduled_time": src.scheduled_time or "",
                        "interval_time": src.interval_time or "",
                    }
                    self._scheduled_triggers.append((meta, scheduled_cfg))

                # 检查设备触发器
                if src.device_trigger_enabled:
                    device_cfg: DeviceTriggerConfig = {
                        "device_trigger_enabled": True,
                        "target": src.target_path or "",
                        "auto_mount": src.auto_mount,
                        "mount_point": src.mount_point or "",
                    }
                    self._device_triggers.append((meta, device_cfg))

            # 在锁内复制触发器列表，避免后续操作期间列表被修改
            scheduled_snapshot = list(self._scheduled_triggers)

        # 同步调度任务（在锁外执行，避免阻塞其他线程）
        self._worker.sync_jobs(scheduled_snapshot)

        self._logger.info(
            "Loaded %d scheduled trigger(s) and %d device trigger(s)",
            len(self._scheduled_triggers),
            len(self._device_triggers),
        )

    def _execute_scheduled_callbacks(self, source_id: str) -> None:
        """Worker 触发时调用，执行该 source 的所有计划回调。"""
        with self._lock:
            callbacks = self._scheduled_callbacks.get(source_id, [])
            # 复制列表，避免回调执行期间修改字典
            callbacks = list(callbacks)

        for cb in callbacks:
            # noinspection PyBroadException
            try:
                cb()
            except Exception:
                self._logger.exception("Callback failed for source %s", source_id)

    def add_scheduled_callback(self, source_id: str, callback: Callable[..., Any]) -> bool:
        """为指定的计划触发器添加回调函数。

        Args:
            source_id: 源 ID，用于定位触发器。
            callback: 可调用对象，将在触发器触发时被调用。

        Returns:
            是否成功添加（找到对应触发器且回调有效）。
        """
        if not callable(callback):
            raise TypeError("callback must be callable")

        # source_id = str(source_id)

        with self._lock:
            # 检查触发器是否存在
            if not any(meta["source_id"] == source_id for meta, _ in self._scheduled_triggers):
                self._logger.warning("No scheduled trigger found for source %s", source_id)
                return False

            if source_id not in self._scheduled_callbacks:
                self._scheduled_callbacks[source_id] = []
            self._scheduled_callbacks[source_id].append(callback)
            self._logger.debug("Added scheduled callback for source %s", source_id)
            return True

    def add_device_callback(self, source_id: str, callback: Callable[..., Any]) -> bool:
        """为指定的设备触发器添加回调函数。

        Args:
            source_id: 源 ID，用于定位触发器。
            callback: 可调用对象，将在触发器触发时被调用。

        Returns:
            是否成功添加（找到对应触发器且回调有效）。
        """
        if not callable(callback):
            raise TypeError("callback must be callable")

        with self._lock:
            if not any(meta["source_id"] == source_id for meta, _ in self._device_triggers):
                self._logger.warning("No device trigger found for source %s", source_id)
                return False

            if source_id not in self._device_callbacks:
                self._device_callbacks[source_id] = []
            self._device_callbacks[source_id].append(callback)
            self._logger.debug("Added device callback for source %s", source_id)
            return True

    def clean_orphan_callbacks(self) -> int:
        """清理所有已失去对应触发器的回调钩子。

        遍历回调字典，若某个 source_id 不再存在于对应的触发器列表中，
        则删除该回调记录。同时删除空列表的条目。

        Returns:
            清理的 source_id 数量（即删除了多少个键）。
        """
        with self._lock:
            cleaned = 0
            # 清理计划回调
            scheduled_ids = {meta["source_id"] for meta, _ in self._scheduled_triggers}
            orphan_scheduled = [sid for sid in self._scheduled_callbacks if sid not in scheduled_ids]
            for sid in orphan_scheduled:
                del self._scheduled_callbacks[sid]
                cleaned += 1
                self._logger.debug("Cleaned orphan scheduled callbacks for source %s", sid)

            # 清理设备回调
            device_ids = {meta["source_id"] for meta, _ in self._device_triggers}
            orphan_device = [sid for sid in self._device_callbacks if sid not in device_ids]
            for sid in orphan_device:
                del self._device_callbacks[sid]
                cleaned += 1
                self._logger.debug("Cleaned orphan device callbacks for source %s", sid)

            if cleaned:
                self._logger.info("Cleaned %d orphan callback group(s)", cleaned)
            return cleaned

    def heartbeat(self) -> str:
        """心跳检查：返回服务状态和已加载触发器及回调数量。"""
        with self._lock:
            status = (
                f"TriggerService alive, "
                f"{len(self._scheduled_triggers)} scheduled triggers, "
                f"{len(self._device_triggers)} device triggers, "
                f"{sum(len(v) for v in self._scheduled_callbacks.values())} scheduled callbacks, "
                f"{sum(len(v) for v in self._device_callbacks.values())} device callbacks"
            )
        self._logger.info(status)
        return status

    def __str__(self) -> str:
        """格式化输出触发器配置及独立存储的回调状态。"""
        with self._lock:
            scheduled_ids = {meta["source_id"] for meta, _ in self._scheduled_triggers}
            device_ids = {meta["source_id"] for meta, _ in self._device_triggers}

            if (not self._scheduled_triggers and not self._device_triggers and
                    not self._scheduled_callbacks and not self._device_callbacks):
                return "No triggers or callbacks loaded."

            lines = []

            if self._scheduled_triggers or self._device_triggers:
                lines.append("Loaded triggers:")
                if self._scheduled_triggers:
                    lines.append("  Scheduled:")
                    for meta, cfg in self._scheduled_triggers:
                        callbacks = self._scheduled_callbacks.get(str(meta["source_id"]))
                        cb_count = len(callbacks) if callbacks else 0
                        lines.append(
                            f"    - id={meta['source_id']}, title='{meta['title']}', "
                            f"source='{meta['source_path']}', "
                            f"time='{cfg['scheduled_time'] or cfg['interval_time']}', "
                            f"callbacks={cb_count}"
                        )
                if self._device_triggers:
                    lines.append("  Device:")
                    for meta, cfg in self._device_triggers:
                        callbacks = self._device_callbacks.get(str(meta["source_id"]))
                        cb_count = len(callbacks) if callbacks else 0
                        lines.append(
                            f"    - id={meta['source_id']}, title='{meta['title']}', "
                            f"source='{meta['source_path']}', target='{cfg['target']}', "
                            f"callbacks={cb_count}"
                        )

            if self._scheduled_callbacks or self._device_callbacks:
                lines.append("Callback storage:")
                if self._scheduled_callbacks:
                    lines.append("  Scheduled callbacks:")
                    for sid, cbs in self._scheduled_callbacks.items():
                        orphan = sid not in scheduled_ids
                        lines.append(
                            f"    - source_id={sid}, count={len(cbs)}, orphan={orphan}"
                        )
                if self._device_callbacks:
                    lines.append("  Device callbacks:")
                    for sid, cbs in self._device_callbacks.items():
                        orphan = sid not in device_ids
                        lines.append(
                            f"    - source_id={sid}, count={len(cbs)}, orphan={orphan}"
                        )

            return "\n".join(lines)
