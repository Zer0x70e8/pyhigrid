#
""""""

import logging
from typing import List, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from albuswall.domain.types import ScheduledTriggerConfig, ScheduledTriggerTuple


class SchedulerWorker:
    """封装 APScheduler，负责定时任务的调度与执行。

    该 worker 仅处理计划触发器（scheduled triggers），设备触发器通常由其他
    事件驱动机制（如 udev）触发，不在此处调度。
    """

    def __init__(self, executor: Callable[[str], None]):
        """
        Args:
            executor: 回调执行函数，接收 source_id 作为参数，由外部（TriggerService）
                      提供，当调度任务触发时调用。
        """
        self._executor = executor
        self._scheduler = BackgroundScheduler()
        self._logger = logging.getLogger(__name__)

    def start(self) -> None:
        """启动调度器。"""
        if not self._scheduler.running:
            self._scheduler.start()
            self._logger.info("Scheduler started")

    def stop(self) -> None:
        """停止调度器（不等待正在执行的任务完成）。"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            self._logger.info("Scheduler stopped")

    def sync_jobs(self, scheduled_triggers: List[ScheduledTriggerTuple]) -> None:
        """根据传入的触发器列表同步调度任务。

        为简化实现，先移除所有现有任务，再按当前配置重新添加。
        对于小型系统足够，若需增量更新可在此方法中扩展。

        Args:
            scheduled_triggers: 当前的计划触发器列表，每个元素为 (meta, config)。
        """
        self._logger.debug("Synchronizing jobs with %d triggers", len(scheduled_triggers))

        # 移除所有现有任务
        self._scheduler.remove_all_jobs()

        for meta, cfg in scheduled_triggers:
            source_id = str(meta["source_id"])
            trigger = self._build_trigger(cfg)
            if trigger is None:
                self._logger.warning(
                    "Cannot build trigger for source %s, skipping", source_id
                )
                continue

            try:
                self._scheduler.add_job(
                    self._job_wrapper,
                    trigger=trigger,
                    id=source_id,
                    args=[source_id],
                    replace_existing=True,
                )
                self._logger.debug("Added job for source %s", source_id)
            except Exception as e:
                self._logger.exception("Failed to add job for source %s: %s", source_id, e)

    def _build_trigger(self, cfg: ScheduledTriggerConfig):
        """根据配置构建 APScheduler 触发器对象。

        优先使用 scheduled_time（cron 表达式），其次使用 interval_time（秒数）。
        若两者都为空则返回 None。
        """
        scheduled_time = cfg.get("scheduled_time")
        interval_time = cfg.get("interval_time")

        if scheduled_time:
            try:
                return CronTrigger.from_crontab(scheduled_time)
            except Exception as e:
                self._logger.error("Invalid cron expression '%s': %s", scheduled_time, e)
                return None

        if interval_time:
            try:
                seconds = int(interval_time)
                if seconds <= 0:
                    raise ValueError("interval must be positive")
                return IntervalTrigger(seconds=seconds)
            except (ValueError, TypeError) as e:
                self._logger.error("Invalid interval '%s': %s", interval_time, e)
                return None

        return None

    def _job_wrapper(self, source_id: str) -> None:
        """APScheduler 任务入口，调用外部执行器并捕获异常。"""
        # noinspection PyBroadException
        try:
            self._executor(source_id)
        except Exception:
            self._logger.exception("Error executing callbacks for source %s", source_id)
