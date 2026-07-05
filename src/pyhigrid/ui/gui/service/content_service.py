#
"""
内容业务服务层
负责资产查询、缩略图异步生成，不依赖任何 UI 类型。
"""

from pathlib import Path
from typing import Callable, Dict, Optional, Tuple
from pyhigrid.domain.constants import THUMB_SIZE_SMALL, THUMB_SIZE_MEDIUM, THUMB_SIZE_LARGE

from PySide6.QtCore import QObject, QThread

from pyhigrid.core.bootstrapper.container import Container
from pyhigrid.core.build_logger import TRACE
from pyhigrid.repository import (
    ViewRepository,
    ViewAssetRepository,
    AssetEditRepository,
)

from ..server.thumbnail.generator import ThumbnailGenerator
from ..server.thumbnail.thumbnail_file_writer import ThumbnailFileWriter
from ..utils.loggers import get_logger


MAX_WORKERS = 5


class _PersistWorker(QThread):
    def __init__(self, asset_uuids, service, parent=None):
        super().__init__(parent)
        self.asset_uuids = asset_uuids
        self.service = service
        # ★ 不再连接 finished 到 deleteLater，由 ContentService 统一管理

    def run(self):
        # noinspection PyBroadException
        try:
            self.service.generate_and_persist_thumbnails(self.asset_uuids)
        except Exception:
            pass  # 日志已在 generate_and_persist_thumbnails 中记录


class ContentService(QObject):
    """
    内容服务（纯业务逻辑）

    职责：
    - 根据视图 ID 获取资产数量
    - 异步生成可见范围内的缩略图（返回原始 PNG 字节）
    - 管理缩略图请求的并发过期
    """

    _PRESET_SIZES = [THUMB_SIZE_SMALL, THUMB_SIZE_MEDIUM, THUMB_SIZE_LARGE]

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self._thumb_base_dir = None

        self._persist_workers = []

        # obj
        self._logger = get_logger(self, parent)
        self._thumbnail_gen = ThumbnailGenerator()
        self._view_repo: Optional[ViewRepository] = None
        self._view_asset_repo: Optional[ViewAssetRepository] = None
        self._edit_repo: Optional[AssetEditRepository] = None

        # status
        self._current_view_id: Optional[str] = None
        self._latest_request_id = -1
        self._last_request_params: Optional[Tuple[int, int, int, int]] = None
        self._max_workers = MAX_WORKERS

    # ──── 初始化 ──────────────────────────────────────
    def setup(self, boot_container: Container):
        """
        从容器中注入仓库和缩略图路径配置。
        该方法仅应在应用启动时调用一次。
        """
        # 缩略图目录
        thumbnails_path: Path = boot_container.get("configue").static.path.thumbnails
        self._logger.debug(f"ContentService setup now, "
                          f"thumbnails_path={thumbnails_path}")

        self._thumb_base_dir = str(thumbnails_path)

        if not thumbnails_path.exists():
            thumbnails_path.mkdir(parents=True)

        db = boot_container.get("db")
        self._view_repo = ViewRepository(db)
        self._view_asset_repo = ViewAssetRepository(db)
        self._edit_repo = AssetEditRepository(db)

    # ──── 视图管理 ───────────────────────────────────
    def set_current_view(self, view_id: str):
        """切换当前视图，重置请求过期标记"""
        self._current_view_id = view_id
        self._latest_request_id = -1
        self._logger.debug(f"Current view set to {view_id}")

    def get_view_asset_count(self, view_id: str) -> int:
        """查询指定视图的资产总数"""
        if not self._view_repo:
            self._logger.error("Service not initialized (call setup first)")
            return 0
        view = self._view_repo.get_view(view_id)
        return getattr(view, "asset_count", 0)

    # ──── 缩略图请求 ────────────────────────────────
    def request_thumbnails(
            self,
            start: int,
            end: int,
            cell_size: int,  # 实际单元格尺寸
            on_result: Callable[[Dict[int, bytes]], None],
    ):
        """
        异步获取 [start, end] 范围内的缩略图。

        参数：
            on_result: 回调，参数为 {index: png_bytes}，索引从 start 开始计数。
                       若未初始化或无当前视图，回调可能不被触发。
        """

        if not self._current_view_id or not self._view_asset_repo:
            self._logger.warning("Cannot request thumbnails: no view or repo")
            return

        tasks, asset_uuids = self._get_tasks_in_range(start, end)
        if not tasks:
            self._logger.debug("No assets in range, returning empty result")
            on_result({})
            return

        # ★ 新增：触发异步持久化（全尺寸缩略图写入磁盘 + 数据库记录）
        if asset_uuids:
            self._logger.debug(
                "Triggering async thumbnail persistence for %d assets in range [%d-%d]",
                len(asset_uuids), start, end
            )
            self.request_persist_thumbnails_async(asset_uuids)

        thumb_size = self._map_to_preset(cell_size)
        self._latest_request_id += 1
        request_id = self._latest_request_id

        # 去重逻辑保持不变 ...
        if self._last_request_params is not None:
            last_start, last_end, last_size, _ = self._last_request_params
            if start == last_start and end == last_end and thumb_size == last_size:
                self._logger.debug("Duplicate request skipped (start=%d, end=%d, size=%d)", start, end, thumb_size)
                return

        self._last_request_params = (start, end, thumb_size, request_id)

        def handle_generated(data: Dict[int, bytes]):
            if request_id == self._latest_request_id:
                on_result(data)
            else:
                self._logger.log(TRACE, f"Discarding stale result for request {request_id}")

        self._logger.debug(
            f"Requesting thumbnails [{start}-{end}] mapped_size={thumb_size} (actual={cell_size}) request_id={request_id}"
        )
        self._thumbnail_gen.generate_async(tasks, thumb_size, handle_generated)

    def _get_tasks_in_range(self, start: int, end: int):
        """
        查询数据库，返回 ( {全局索引: 文件路径}, [资产UUID列表] )。
        """
        assert self._current_view_id, ValueError
        assert self._view_asset_repo, ValueError
        assets = self._view_asset_repo.get_assets(
            self._current_view_id,
            offset=start,
            limit=end - start + 1,
        )
        tasks = {}
        uuids = []
        for i, asset in enumerate(assets):
            idx = start + i
            tasks[idx] = asset.file_path
            uuids.append(asset.uuid)  # 假设资产对象有 uuid 属性
        return tasks, uuids

    @classmethod
    def _map_to_preset(cls, cell_size: int) -> int:
        """返回不小于 cell_size 的最小预设尺寸"""
        for size in cls._PRESET_SIZES:
            if size >= cell_size:
                return size
        return cls._PRESET_SIZES[-1]

    def generate_and_persist_thumbnails(self, asset_uuids: list[str]):
        """
        为指定资产生成所有预设尺寸的缩略图文件，并写入数据库。
        此方法会检查文件是否已存在以避免重复生成。
        """
        if not self._view_asset_repo or not self._edit_repo:
            self._logger.warning("Repositories not initialized")
            return

        tasks = {}
        for uuid in asset_uuids:
            detail = self._view_asset_repo.get_asset_detail(uuid)
            if not detail or not detail.file_path:
                continue
            # 检查是否已有任一种缩略图文件（简单避免重复生成）
            existing = self._edit_repo.debugger_asset_info_get(uuid)
            if existing and existing.get("thumb_path"):
                # 假设如果已有 thumb_path 则三种尺寸都生成过，可跳过
                # 更健壮的逻辑应逐个文件检查，此处简化
                continue
            tasks[uuid] = detail.file_path

        if not tasks:
            return

        self._logger.info(f"Generating thumbnail files for {len(tasks)} assets")
        writer = ThumbnailFileWriter(max_workers=self._max_workers)  # _max_workers 可复用
        # noinspection PyBroadException
        try:
            results = writer.process_batch(tasks, self._thumb_base_dir)
            # 更新数据库
            for uuid, paths in results.items():
                if any(paths.values()):  # 至少生成了一张
                    self._edit_repo.update(
                        uuid,
                        thumb_path=paths.get("large", ""),
                        thumb_small_path=paths.get("small", ""),
                        thumb_medium_path=paths.get("medium", "")
                    )
        except Exception:
            self._logger.exception("Bulk thumbnail generation failed")
        finally:
            writer.shutdown()

    def request_persist_thumbnails_async(self, asset_uuids: list[str]):
        """异步生成缩略图文件并写库"""
        self._logger.info("Async persist requested for %d assets", len(asset_uuids))
        worker = _PersistWorker(asset_uuids, self)
        # 连接 finished 信号，在完成后移除引用并清理
        worker.finished.connect(lambda w=worker: self._on_persist_worker_finished(w))
        self._persist_workers.append(worker)  # 保持强引用
        worker.start()

    def _on_persist_worker_finished(self, worker):
        """持久化线程完成后的清理"""
        if worker in self._persist_workers:
            self._persist_workers.remove(worker)
        worker.deleteLater()
