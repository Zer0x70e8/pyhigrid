#
""""""
import threading
import queue
import logging
from typing import List, Optional, Union, Dict, Any

from albuswall.repository.importer import (
    ImportRepository,
    FileImportInfo,
    BatchImportResult,
)

logger = logging.getLogger("__main__.service.import")


class ImportTask:
    """封装一次导入任务，提供同步等待接口"""
    def __init__(self, files: List[Union[FileImportInfo, Dict[str, Any]]],
                 album_uuids: Optional[List[str]] = None):
        self.files = files
        self.album_uuids = album_uuids
        self.result: Optional[BatchImportResult] = None
        self.error: Optional[Exception] = None
        self._done_event = threading.Event()

    def wait(self, timeout: Optional[float] = None) -> bool:
        """等待任务完成，返回是否在超时前完成"""
        return self._done_event.wait(timeout)

    def done(self) -> bool:
        """任务是否已完成"""
        return self._done_event.is_set()

    def _set_done(self, result: BatchImportResult = None, error: Exception = None):
        self.result = result
        self.error = error
        self._done_event.set()


class ImportService:
    """
    后台导入服务。

    维护一个单工作线程，所有数据库导入操作在该线程中串行执行，
    从而避免 SQLite 并发冲突，并保持主进程响应能力。
    """

    def __init__(self, repository: ImportRepository):
        """
        :param repository: 已配置好的 ImportRepository 实例
        """
        self._repo = repository
        self._task_queue: queue.Queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # --------------- 生命周期管理 ---------------
    def start(self):
        """启动后台工作线程（守护线程）"""
        if self._worker_thread and self._worker_thread.is_alive():
            logger.warning("导入服务已在运行")
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._worker_loop, name="ImportWorker", daemon=True
        )
        self._worker_thread.start()
        logger.info("导入服务工作线程已启动")

    def stop(self, timeout: Optional[float] = None):
        """停止后台线程（等待当前任务完成）"""
        if not self._worker_thread or not self._worker_thread.is_alive():
            return
        self._stop_event.set()
        # 放入哨兵对象唤醒线程
        self._task_queue.put(None)
        self._worker_thread.join(timeout=timeout)
        if self._worker_thread.is_alive():
            logger.warning("导入服务线程未能在 %.1f 秒内停止", timeout or -1)
        else:
            logger.info("导入服务已停止")

    # --------------- 任务提交 ---------------
    def submit_import(self,
                      files: List[Union[FileImportInfo, Dict[str, Any]]],
                      album_uuids: Optional[List[str]] = None) -> ImportTask:
        """
        异步提交批量导入任务。

        :param files: 待导入文件信息列表
        :param album_uuids: 额外关联的相簿 UUID 列表
        :return: ImportTask 对象，可通过 wait() 等待完成并获取结果
        """
        task = ImportTask(files, album_uuids)
        self._task_queue.put(task)
        return task

    # --------------- 工作线程 ---------------
    def _worker_loop(self):
        """工作线程主循环，从队列获取任务并执行"""
        while not self._stop_event.is_set():
            try:
                task = self._task_queue.get(timeout=1.0)  # 1秒超时以便检查停止信号
            except queue.Empty:
                continue
            if task is None:  # 停止哨兵
                break
            self._execute_task(task)
            self._task_queue.task_done()

    def _execute_task(self, task: ImportTask):
        """执行单个导入任务"""
        try:
            # 调用仓库层的批量导入方法（内部已处理事务、去重等）
            result = self._repo.batch_import_files(task.files, task.album_uuids)
            # noinspection PyProtectedMember
            task._set_done(result=result)
        except Exception as e:
            logger.exception("批量导入执行失败")
            # noinspection PyProtectedMember
            task._set_done(error=e)
