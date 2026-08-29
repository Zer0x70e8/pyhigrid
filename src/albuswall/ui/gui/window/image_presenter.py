#
"""
内容业务服务层
负责资产查询、缩略图异步生成
"""

from pathlib import Path
from typing import Callable, Dict, Optional, Tuple
from albuswall.domain.constants import THUMB_SIZE_SMALL, THUMB_SIZE_MEDIUM, THUMB_SIZE_LARGE

from PySide6.QtCore import QObject, QThread

from albuswall.core.bootstrapper.container import Container
from albuswall.core.build_logger import TRACE
from albuswall.repositories import (
    ViewRepository,
    ViewAssetRepository,
    AssetEditRepository,
    IngestSourceRepository,
)

from albuswall.ui.gui.service.thumbnail.generator import ThumbnailGenerator
from albuswall.ui.gui.service.thumbnail.thumbnail_file_writer import ThumbnailFileWriter
from albuswall.ui.gui.utils.loggers import get_logger


MAX_WORKERS = 5


class _PersistWorker(QThread):
    def __init__(self, asset_uuids, service, parent=None):
        super().__init__(parent)
        self.asset_uuids = asset_uuids
        self.service = service

    def run(self):
        self.service.generate_and_persist_thumbnails(self.asset_uuids)


class ImagePresenter(QObject):
    """
    内容服务（纯业务逻辑）

    职责：
    - 根据视图 ID 获取资产数量
    - 异步生成可见范围内的缩略图（返回原始 PNG 字节）
    - 管理缩略图请求的并发过期
    """

    _PRESET_SIZES = [THUMB_SIZE_SMALL, THUMB_SIZE_MEDIUM, THUMB_SIZE_LARGE]

    _view_repo: ViewRepository
    _view_asset_repo: ViewAssetRepository
    _edit_repo: AssetEditRepository
    _source_repo: IngestSourceRepository

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self._thumb_base_dir = None

        self._persist_workers = []

        # obj
        self._logger = get_logger(self, parent)
        self._thumbnail_gen = ThumbnailGenerator()

        # status
        self._current_view_id: Optional[str] = None
        self._latest_request_id = -1
        self._last_request_params: Optional[Tuple[int, int, int, int]] = None
        self._max_workers = MAX_WORKERS

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

        self._view_repo = boot_container.get("view_repo")
        self._view_asset_repo = boot_container.get("view_asset_repo")
        self._edit_repo = boot_container.get("asset_edit_repo")
        self._source_repo = boot_container.get("ingest_source_repo")

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
        查询数据库，返回 ( {全局索引: 完整文件路径}, [资产UUID列表] )。
        文件路径会根据资产的 source_id 拼接对应导入源的基础路径。
        """
        assert self._current_view_id, ValueError
        assert self._view_asset_repo, ValueError
        assert self._source_repo, ValueError

        assets = self._view_asset_repo.get_assets(
            self._current_view_id,
            offset=start,
            limit=end - start + 1,
        )

        # 1. 收集所有出现过的 source_id（仅接受 int 类型）
        source_ids: set[int] = set()
        for asset in assets:
            sid = getattr(asset, 'source_id', None)
            if isinstance(sid, int):
                source_ids.add(sid)

        # 2. 批量查询导入源，构建 source_id -> 基础路径 的映射
        source_base_map: dict[int, str] = {}
        if source_ids:
            for source_id in source_ids:
                source_record = self._source_repo.get_by_id(source_id)
                if source_record:
                    # 优先使用 source_path，其次 target_path，最后 mount_point
                    base = (
                            source_record.source_path
                            or source_record.target_path
                            or source_record.mount_point
                            or ''
                    )
                    if base:
                        source_base_map[source_id] = base
                    else:
                        self._logger.warning(
                            f"导入源 {source_id} 没有可用的基础路径字段"
                        )
                else:
                    self._logger.warning(f"导入源 {source_id} 不存在于数据库中")

        # 3. 构建任务字典，拼接完整路径
        tasks: dict[int, str] = {}
        uuids: list[str] = []
        for i, asset in enumerate(assets):
            idx = start + i
            file_path = getattr(asset, 'file_path', '') or ''
            source_id = getattr(asset, 'source_id', None)

            # 仅当 source_id 是 int 且存在于映射中时才拼接路径
            if isinstance(source_id, int) and source_id in source_base_map:
                base = source_base_map[source_id]
                full_path = str(Path(base) / file_path) if file_path else ''
            else:
                full_path = file_path
                if isinstance(source_id, int):
                    self._logger.warning(
                        f"资产 {getattr(asset, 'uuid', '')} 的导入源 {source_id} 无法解析基础路径，"
                        f"将使用原始文件名: {file_path}"
                    )

            tasks[idx] = full_path
            uuids.append(getattr(asset, 'uuid', ''))

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

    def get_asset_file_path(self, index: int) -> Optional[str]:
        """返回当前视图中指定索引的资源绝对文件路径，失败返回 None"""
        if not self._current_view_id or not self._view_asset_repo:
            return None
        assets = self._view_asset_repo.get_assets(
            self._current_view_id, offset=index, limit=1
        )
        if not assets:
            return None

        asset = assets[0]
        file_path = getattr(asset, 'file_path', '') or ''
        source_id = getattr(asset, 'source_id', None)

        # 若 source_id 无效或文件名缺失，直接返回原始文件名（可能为空）
        if not isinstance(source_id, int) or not file_path:
            return file_path or None

        # 尝试从导入源仓库查询基础路径
        if self._source_repo:
            source_record = self._source_repo.get_by_id(source_id)
            if source_record:
                base = (
                        source_record.source_path
                        or source_record.target_path
                        or source_record.mount_point
                        or ''
                )
                if base:
                    return str(Path(base) / file_path)

        # 若未能拼接，返回原始文件名
        return file_path or None
