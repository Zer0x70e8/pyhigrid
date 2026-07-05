#
"""
缩略图异步生成器（UI 基础设施）
使用 Pillow 离线处理图片，通过 ProcessPoolExecutor + QThread 避免阻塞主线程
同时解决多线程下 PIL/C 扩展的段错误 (SIGSEGV) 问题
"""

import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from io import BytesIO
from typing import Dict, Callable, Optional

from PIL import Image, ImageOps
from PySide6.QtCore import QObject, QThread, Signal, Slot

from ._logger import logger

from pyhigrid.core.build_logger import TRACE


# ============================================================
# 模块级图像处理函数（供子进程调用）
# ============================================================
def _process_single_image(file_path: str, cell_size: int) -> bytes:
    """
    在子进程中执行，打开图像、缩放并返回 PNG 字节。
    任何异常都返回空字节，由主进程记录日志。
    """
    try:
        with Image.open(file_path) as img:
            img.load()
            img = ImageOps.fit(
                img, (cell_size, cell_size),
                method=Image.Resampling.LANCZOS
            )
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
    except Exception:
        return b""


# ============================================================
# 后台工作线程：管理进程池，收集结果并通过信号发回主线程
# ============================================================
class _ThumbnailWorker(QThread):
    """
    在一个独立线程中运行 ProcessPoolExecutor，
    每完成一个任务发射 task_done(idx, data) 信号（连接到主线程的槽）。
    即使线程内部发生未预期异常，也会保证所有任务被标记为失败，避免调用方永久挂起。
    """
    task_done = Signal(int, int, bytes)        # request_id, index, data
    error_occurred = Signal(int, int, str)     # request_id, index, error_msg

    def __init__(self, request_id: int, tasks: Dict[int, str], 
                 cell_size: int, max_workers: int = 4, parent=None):
        super().__init__(parent)
        self.request_id = request_id
        self.tasks = tasks
        self.cell_size = cell_size
        self.max_workers = max_workers

    def run(self) -> None:
        """
        使用进程池处理所有任务。任何未捕获的异常都会被拦截，
        以确保对未完成的任务发射空结果，并最终安全退出线程。
        """
        future_to_idx = {}
        try:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                for idx, path in self.tasks.items():
                    future = executor.submit(_process_single_image, path, self.cell_size)
                    future_to_idx[future] = idx

                # 处理完成的任务
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        data = future.result()
                    except Exception:
                        data = b""
                        self.error_occurred.emit(
                            self.request_id, idx,
                            f"Subprocess crashed: {traceback.format_exc()}"
                        )
                    self.task_done.emit(self.request_id, idx, data)

        except Exception as e:
            # 线程内出现意外异常（例如在遍历、提交过程中出错）
            error_msg = f"Worker thread unexpected error: {traceback.format_exc()}"
            logger.error(error_msg)
            # 为所有尚未完成的任务发射空结果，防止调用方永久挂起
            for idx in self.tasks.keys():
                if idx not in [future_to_idx[f] for f in future_to_idx if f.done()]:
                    self.task_done.emit(self.request_id, idx, b"")
                    self.error_occurred.emit(self.request_id, idx, error_msg)
            # 发射一个全局错误信号（index = -1 表示批处理级错误）
            self.error_occurred.emit(self.request_id, -1, error_msg)

        # 无论是否发生异常，run() 正常返回，finished 信号得以发射，
        # 从而触发 deleteLater 安全销毁线程对象，避免内存泄漏。


# ============================================================
# 缩略图生成器（QObject，接口完全不变）
# ============================================================
class ThumbnailGenerator(QObject):
    """
    批量异步生成缩略图，通过回调返回结果。

    用法：
        generator = ThumbnailGenerator()
        generator.generate_async(
            tasks={0: "/path/to/img.jpg", 1: "/path/to/img2.png"},
            cell_size=150,
            on_finished=lambda batch: print("Done", batch),
        )
    """

    _single_done = Signal(int, int, bytes)  # request_id, index, data

    def __init__(self, max_threads: int = 4, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._max_workers = max_threads  # 现控制进程池大小
        self._pending: Dict[int, dict] = {}
        self._counter = 0
        self._single_done.connect(self._on_single_done)
        logger.info("ThumbnailGenerator initialized (max_workers=%d)", max_threads)
        logger.log(TRACE, "Using ProcessPoolExecutor with %d workers", max_threads)

    @Slot(int, int, bytes)
    def _on_single_done(self, request_id: int, index: int, data: bytes):
        state = self._pending.get(request_id)
        if state is None:
            logger.warning(
                "Received result for unknown request_id=%d (index=%d)",
                request_id, index,
            )
            return

        # 防御性断言：remaining 不应小于 0（重复发射等异常情况）
        assert state["remaining"] > 0, (
            f"Internal error: remaining count for request {request_id} "
            f"is already 0 when receiving task {index}"
        )

        state["result"][index] = data
        state["remaining"] -= 1
        logger.log(TRACE, 
            "Task done: request_id=%d, index=%d, remaining=%d",
            request_id, index, state["remaining"],
        )

        if state["remaining"] == 0:
            self._finish_batch(request_id)

    def generate_async(
        self,
        tasks: Dict[int, str],
        cell_size: int,
        on_finished: Callable[[Dict[int, bytes]], None],
    ) -> int:
        """
        提交一个批量生成请求，返回 request_id。
        完成后调用 on_finished({index: png_bytes})。
        若某张图片加载失败，其 value 为 b""。
        """
        request_id = self._counter
        self._counter += 1

        # 断言：request_id 必须是唯一的
        assert request_id not in self._pending, (
            f"Internal error: request_id {request_id} already exists in pending"
        )

        logger.info(
            "Starting batch request_id=%d (%d tasks, cell_size=%d)",
            request_id, len(tasks), cell_size,
        )
        logger.log(TRACE, "Batch details: tasks=%s", tasks)

        state = {
            "remaining": len(tasks),
            "result": {},
            "on_finished": on_finished,
        }
        self._pending[request_id] = state

        # 空 tasks 快速路径
        if not tasks:
            logger.info("Empty batch request_id=%d, finishing immediately", request_id)
            self._finish_batch(request_id)
            return request_id

        # 创建并启动工作线程（内部使用进程池）
        worker = _ThumbnailWorker(request_id, tasks, cell_size,
                                  max_workers=self._max_workers,
                                  parent=self)
        worker.task_done.connect(self._single_done)
        worker.error_occurred.connect(self._on_worker_error)
        # 使用 QThread 自带的 finished 信号安全清理（注意不是 task_done）
        worker.finished.connect(worker.deleteLater)
        worker.start()

        # 记录已分派的任务
        for idx, path in tasks.items():
            logger.log(TRACE, "Dispatched task: request_id=%d, index=%d, path=%s",
                       request_id, idx, path)

        return request_id

    @Slot(int, int, str)
    def _on_worker_error(self, request_id: int, index: int, error_msg: str):
        """处理子进程级错误（如崩溃）或线程级错误"""
        if index == -1:
            logger.error(
                "Batch-level error for request_id=%d: %s",
                request_id, error_msg
            )
        else:
            logger.error(
                "Subprocess error for request_id=%d, index=%d: %s",
                request_id, index, error_msg
            )

    def _finish_batch(self, request_id: int):
        """
        结束批次处理，调用用户回调。
        使用 try...finally 确保回调异常不会干扰状态清理。
        """
        state = self._pending.pop(request_id, None)
        if not state:
            logger.warning("Attempted to finish unknown batch request_id=%d", request_id)
            return

        logger.info("Finishing batch request_id=%d, result_size=%d",
                    request_id, len(state["result"]))
        logger.log(TRACE, "Batch finished: request_id=%d", request_id)

        # 防御性断言：正常完成时 remaining 应为 0
        assert state["remaining"] == 0, (
            f"Internal error: batch request_id={request_id} finished "
            f"with remaining={state['remaining']} (expected 0)"
        )

        try:
            state["on_finished"](state["result"])
        except Exception:
            logger.exception(
                "Unhandled exception in on_finished callback for request_id=%d",
                request_id
            )
        # 注意：state 已从 _pending 弹出，即使回调抛异常也不会残留
