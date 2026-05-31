#
""""""

import os
from typing import List, OrderedDict, Optional

from PySide6.QtCore import QObject, QMutex, QMutexLocker, Qt
from PySide6.QtGui import QImage, QImageReader

from pyhigrid.domain.enums import AssetImageType, AlbumAssetSortOption
from ...widget.virtual_scroll.utils import image_provider
from ..datatypes import AssetThumbData, AlbumInfo


class AssetImageProvider(QObject):
    """
    为虚拟滚动组件提供缩略图的异步数据源。
    所有工作线程调用的方法均为线程安全（除 GUI 回调外）。
    """

    def __init__(
        self,
        album_repo,
        thumbnail_type: AssetImageType = AssetImageType.THUMB_SMALL,
    ):
        super().__init__()
        self._repo = album_repo
        self._thumbnail_type = thumbnail_type
        self._items: List[AssetThumbData] = []      # 现在使用 dataclass 列表
        self._album_info: Optional[AlbumInfo] = None
        self._mutex = QMutex()
        self._cache: OrderedDict[int, QImage] = OrderedDict()
        self._max_cache = 200

    # ---------- 数据加载 ----------
    def load_album(
        self,
        album_id: int,
        sort_by: AlbumAssetSortOption = AlbumAssetSortOption.TAKEN_AT,
    ):
        """
        加载指定相簿的 **全部** 资产 ID 与路径信息。
        自动分页拉取，线程安全。
        """
        # 先获取相簿元信息（用于 AlbumInfo）
        album_dict = self._repo.get_album(album_id)
        if not album_dict:
            self._clear_items()
            return

        # ---------- 分页拉取全部资产 ----------
        all_assets = []
        page_size = 500
        offset = 0
        while True:
            page = self._repo.get_album_assets(
                album_id, sort_by, limit=page_size, offset=offset
            )
            if not page:
                break
            all_assets.extend(page)
            if len(page) < page_size:   # 已取完
                break
            offset += page_size

        # ---------- 转换为 AssetThumbData ----------
        new_items: List[AssetThumbData] = []
        for a in all_assets:
            td = AssetThumbData(
                uuid=a.get("uuid", ""),
                thumb_small=a.get("thumb_small_path"),
                thumb_medium=a.get("thumb_medium_path"),
                thumb_large=a.get("thumb_path"),       # 注意仓库字段名
                original_path=a.get("file_path"),
            )
            new_items.append(td)

        # ---------- 构建 AlbumInfo ----------
        cover = self._repo.get_album_cover(album_id)   # 返回 dict 或 None
        first_uuid = cover.get("uuid") if cover else None

        album_info = AlbumInfo(
            album_id=album_id,
            title=album_dict["title"],
            asset_count=len(new_items),
            first_uuid=first_uuid,
        )

        # 线程安全地更新内部状态
        with QMutexLocker(self._mutex):
            self._items = new_items
            self._album_info = album_info
            self._cache.clear()

    def _clear_items(self):
        with QMutexLocker(self._mutex):
            self._items.clear()
            self._album_info = None
            self._cache.clear()

    # ---------- 对外属性 ----------
    @property
    def total_items(self) -> int:
        with QMutexLocker(self._mutex):
            return len(self._items)

    @property
    def album_info(self) -> Optional[AlbumInfo]:
        with QMutexLocker(self._mutex):
            return self._album_info

    # ---------- 缩略图生成（工作线程调用） ----------
    def get_thumbnail(self, index: int) -> QImage:
        """根据全局索引生成/加载缩略图。线程安全。"""
        # 1. 查缓存
        with QMutexLocker(self._mutex):
            if index in self._cache:
                img = self._cache.pop(index)
                self._cache[index] = img   # 移到末尾（LRU）
                return img

            if index < 0 or index >= len(self._items):
                return self._create_placeholder(index)

            item = self._items[index]      # 此时已持有锁，但下面释放锁后仍使用 item 引用
                                           # 因为 self._items 不会被删除元素，安全

        # 2. 优先使用已存在的缩略图文件
        thumb_path = self._get_thumb_path(item)
        if thumb_path and os.path.isfile(thumb_path):
            img = self._load_image(thumb_path)
            if not img.isNull():
                self._add_to_cache(index, img)
                return img

        # 3. 回退：用原图实时生成缩略图
        if item.original_path and os.path.isfile(item.original_path):
            img = self._generate_thumbnail_from_original(item.original_path)
            if not img.isNull():
                self._add_to_cache(index, img)
                return img

        # 4. 完全失败：返回占位图
        return self._create_placeholder(index)

    def _get_thumb_path(self, item: AssetThumbData) -> Optional[str]:
        """根据当前缩略图类型返回可能存在的文件路径"""
        if self._thumbnail_type == AssetImageType.THUMB_SMALL:
            return item.thumb_small
        elif self._thumbnail_type == AssetImageType.THUMB_MEDIUM:
            return item.thumb_medium
        elif self._thumbnail_type == AssetImageType.THUMB_LARGE:
            return item.thumb_large
        return None

    @staticmethod
    def _load_image(path: str) -> QImage:
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        return reader.read()

    def _generate_thumbnail_from_original(self, original_path: str) -> QImage:
        max_size = getattr(self._thumbnail_type, "max_size", 256)
        reader = QImageReader(original_path)
        reader.setAutoTransform(True)
        orig_size = reader.size()
        if orig_size.isValid():
            scaled = orig_size.scaled(max_size, max_size, Qt.KeepAspectRatio)
            reader.setScaledSize(scaled)
        return reader.read()

    def _add_to_cache(self, index: int, img: QImage):
        with QMutexLocker(self._mutex):
            self._cache[index] = img
            while len(self._cache) > self._max_cache:
                self._cache.popitem(last=False)

    @staticmethod
    def _create_placeholder(index: int) -> QImage:
        # 继续复用原有的占位图生成函数
        return image_provider(index)

    # ---------- 单个资产数据获取（供外部按需调用） ----------
    def get_item(self, index: int) -> Optional[AssetThumbData]:
        with QMutexLocker(self._mutex):
            if 0 <= index < len(self._items):
                return self._items[index]
        return None
