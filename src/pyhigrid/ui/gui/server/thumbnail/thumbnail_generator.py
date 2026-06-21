#
"""
thumbnail_generator.py
异步缩略图生成器，以 max_size 为维度管理缓存。
- 支持通过 AssetImageType 枚举直接请求对应尺寸的缩略图。
- 缓存目录按 max_size 分文件夹，避免不同尺寸冲突。
- 利用 PNG 文本块记录原图 mtime、URI 等元数据，用于缓存有效性验证。
- 线程池异步生成，支持优先级请求、取消任务与失败标记。
- 通过信号通知 UI 缩略图已就绪。
"""

import os
import hashlib
from typing import Optional, Set

from PySide6.QtCore import (
    QObject,
    Signal,
    QThreadPool,
    QRunnable,
    QMutex,
    QMutexLocker,
    QMetaObject,
    Qt,
    Slot,
    QSize,
)
from PySide6.QtGui import QImage, QImageReader

from pyhigrid.domain.enums import AssetImageType


class ThumbnailGenerator(QObject):
    """
    异步缩略图生成器。
    初始化时传入缩略图缓存根目录（绝对路径）。
    缓存结构：<cache_root>/<max_size>/<md5(uri)>.png
    """

    # 信号：缩略图生成完毕
    # uri: 原始文件 file:// URI
    # max_size: 请求的边长（像素）
    # img: 生成的 QImage（失败时为 null）
    thumbnail_ready = Signal(str, int, QImage)

    # PNG 元数据键名（遵循 Freedesktop Thumbnail Standard）
    META_URI = "Thumb::URI"
    META_MTIME = "Thumb::MTime"
    META_SIZE = "Thumb::Size"
    META_MIMETYPE = "Thumb::Mimetype"

    def __init__(self, cache_root: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        if not os.path.isabs(cache_root):
            raise ValueError("cache_root must be an absolute path")
        self._cache_root = cache_root

        # 线程池
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(max(2, os.cpu_count() or 4))

        # 并发控制
        self._mutex = QMutex()
        self._pending: Set[str] = set()  # 格式: f"{file_uri}:{max_size}"
        self._failed: Set[str] = set()   # 失败标记

    # -------------------------------
    # 公共接口
    # -------------------------------
    def request(self, uri: str, max_size: int, priority: int = 0):
        """
        请求生成指定文件的缩略图。
        :param uri: 原始文件的绝对路径（或 file:// URI）
        :param max_size: 目标缩略图最大边长（像素）
        :param priority: 优先级（预留）
        """
        if not uri or max_size <= 0:
            return

        file_uri = self._ensure_uri(uri)
        abs_path = self._abs_path_from_uri(file_uri)
        if not os.path.isfile(abs_path):
            return

        task_key = f"{file_uri}:{max_size}"
        with QMutexLocker(self._mutex):
            if task_key in self._pending or task_key in self._failed:
                return
            cache_path = self._cache_path(file_uri, max_size)
            if self._is_cache_valid(abs_path, file_uri, cache_path):
                return  # 缓存有效，无需重新生成
            self._pending.add(task_key)

        task = _ThumbnailTask(
            generator=self,
            file_path=abs_path,
            file_uri=file_uri,
            max_size=max_size,
            cache_path=cache_path,
        )
        self._pool.start(task)

    def request_for_type(self, uri: str, asset_type: AssetImageType, priority: int = 0):
        """
        根据 AssetImageType 枚举请求缩略图。
        ORIGINAL 类型（max_size 为 None）会被忽略。
        """
        if asset_type.max_size is not None:
            self.request(uri, asset_type.max_size, priority)

    def cancel(self, uri: str, max_size: int):
        """取消指定缩略图的生成（如果尚未开始）。"""
        file_uri = self._ensure_uri(uri)
        task_key = f"{file_uri}:{max_size}"
        with QMutexLocker(self._mutex):
            self._pending.discard(task_key)

    def clear_failed(self):
        """清除所有失败标记，允许重新尝试生成。"""
        with QMutexLocker(self._mutex):
            self._failed.clear()

    # -------------------------------
    # 内部方法（主线程安全）
    # -------------------------------
    @Slot(str, int, str)
    def _on_task_finished(self, file_uri: str, max_size: int, cache_path: str):
        task_key = f"{file_uri}:{max_size}"
        with QMutexLocker(self._mutex):
            if task_key not in self._pending:
                return
            self._pending.remove(task_key)

        img = QImage()
        if os.path.isfile(cache_path):
            img = QImage(cache_path)
            if img.isNull():
                self._mark_failed(task_key)
        else:
            self._mark_failed(task_key)

        self.thumbnail_ready.emit(file_uri, max_size, img)

    def _mark_failed(self, task_key: str):
        with QMutexLocker(self._mutex):
            self._failed.add(task_key)

    def _ensure_uri(self, uri: str) -> str:
        if not uri.startswith("file://"):
            return f"file://{os.path.abspath(uri)}"
        return uri

    def _abs_path_from_uri(self, file_uri: str) -> str:
        from urllib.parse import urlparse, unquote
        parsed = urlparse(file_uri)
        return unquote(parsed.path)

    def _cache_path(self, file_uri: str, max_size: int) -> str:
        """缓存路径：<cache_root>/<max_size>/<md5(uri)>.png"""
        uri_hash = hashlib.md5(file_uri.encode("utf-8")).hexdigest()
        size_dir = str(max_size)
        return os.path.join(self._cache_root, size_dir, f"{uri_hash}.png")

    def _is_cache_valid(self, abs_path: str, file_uri: str, cache_path: str) -> bool:
        """通过 PNG 元数据检查缓存是否仍对应原文件。"""
        if not os.path.isfile(cache_path):
            return False
        try:
            reader = QImageReader(cache_path)
            reader.setAutoTransform(False)
            if not reader.canRead():
                return False
            img = reader.read()
            if img.isNull():
                return False

            cached_uri = img.text(self.META_URI)
            cached_mtime = img.text(self.META_MTIME)
            if cached_uri != file_uri or cached_mtime is None:
                return False
            if cached_mtime != str(int(os.path.getmtime(abs_path))):
                return False

            # 可选文件大小校验
            cached_size = img.text(self.META_SIZE)
            if cached_size is not None:
                if cached_size != str(os.path.getsize(abs_path)):
                    return False
            return True
        except Exception:
            return False


# -------------------------------
# 线程任务
# -------------------------------
class _ThumbnailTask(QRunnable):
    def __init__(
        self,
        generator: ThumbnailGenerator,
        file_path: str,
        file_uri: str,
        max_size: int,
        cache_path: str,
    ):
        super().__init__()
        self._generator = generator
        self._file_path = file_path
        self._file_uri = file_uri
        self._max_size = max_size
        self._cache_path = cache_path
        self._task_key = f"{file_uri}:{max_size}"

    def run(self):
        with QMutexLocker(self._generator._mutex):
            if self._task_key not in self._generator._pending:
                return  # 已被取消

        try:
            img = self._generate()
            if img.isNull():
                self._create_fail_marker()
            else:
                self._save_png(img)
        except Exception:
            self._create_fail_marker()
        finally:
            QMetaObject.invokeMethod(
                self._generator,
                "_on_task_finished",
                Qt.QueuedConnection,
                self._file_uri,
                self._max_size,
                self._cache_path,
            )

    def _generate(self) -> QImage:
        reader = QImageReader(self._file_path)
        if not reader.canRead():
            return QImage()

        max_size = self._max_size
        orig_size = reader.size()
        if orig_size.width() <= 0 or orig_size.height() <= 0:
            return QImage()

        if orig_size.width() <= max_size and orig_size.height() <= max_size:
            reader.setAutoTransform(True)
            return reader.read()

        if orig_size.width() > orig_size.height():
            w = max_size
            h = int(orig_size.height() * max_size / orig_size.width())
        else:
            h = max_size
            w = int(orig_size.width() * max_size / orig_size.height())

        reader.setScaledSize(QSize(w, h))
        reader.setAutoTransform(True)
        return reader.read()

    def _save_png(self, img: QImage):
        img.setText(ThumbnailGenerator.META_URI, self._file_uri)
        mtime = str(int(os.path.getmtime(self._file_path)))
        img.setText(ThumbnailGenerator.META_MTIME, mtime)
        try:
            fsize = str(os.path.getsize(self._file_path))
            img.setText(ThumbnailGenerator.META_SIZE, fsize)
        except OSError:
            pass

        import mimetypes
        mime, _ = mimetypes.guess_type(self._file_path)
        if mime:
            img.setText(ThumbnailGenerator.META_MIMETYPE, mime)

        # 原子写入
        os.makedirs(os.path.dirname(self._cache_path), exist_ok=True)
        tmp_path = self._cache_path + f".tmp-{os.getpid()}"
        if not img.save(tmp_path, "PNG", quality=90):
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return
        if os.path.exists(self._cache_path):
            os.unlink(self._cache_path)
        os.rename(tmp_path, self._cache_path)

    def _create_fail_marker(self):
        pass
