#
"""
asset_image_provider.py
为虚拟滚动组件提供线程安全的缩略图数据源。
依赖 ViewAssetRepository，适配 Cell 的异步加载接口。
"""

import os
from typing import List
from collections import OrderedDict

from PySide6.QtCore import QObject, QMutex, QMutexLocker, Signal, Slot
from PySide6.QtGui import QImage, QImageReader

from pyhigrid.domain.enums import AlbumAssetSortOption, AssetImageType
from pyhigrid.domain.entities import AssetItem
from pyhigrid.repository.view_asset import ViewAssetRepository
from .thumbnail_generator import ThumbnailGenerator
from ...widget.virtual_scroll.utils import image_provider


class AssetImageProvider(QObject):
    """视图资产缩略图提供者，支持按 AssetImageType 动态切换缩略图尺寸并异步生成。"""

    data_loaded = Signal(int)               # 通知 UI 资产总数已更新
    thumbnail_size_changed = Signal()       # 缩略图尺寸类型改变
    thumbnail_updated = Signal(int)         # 单个索引的缩略图已更新 (index)

    def __init__(self,
                 asset_repo: ViewAssetRepository,
                 parent=None,
                 thumbnails_path: str = "./thumbnails"):
        super().__init__(parent)
        self._repo = asset_repo
        self._items: List[AssetItem] = []   # 内存索引
        self._mutex = QMutex()
        self._cache: OrderedDict[int, QImage] = OrderedDict()
        self._max_cache = 200
        self._thumbnail_gen = ThumbnailGenerator(thumbnails_path)
        self._thumbnail_gen.thumbnail_ready.connect(self._on_thumbnail_ready)

        # 当前请求的缩略图尺寸类型，默认为大缩略图
        self._thumbnail_type = AssetImageType.THUMB_LARGE

    # ---------------------- 公开接口 ----------------------
    def load_view(self,
                  view_id: str,
                  sort_by: AlbumAssetSortOption = AlbumAssetSortOption.TAKEN_AT):
        """
        全量加载视图内所有资产（分页拉尽）。
        **务必在工作线程中调用**，避免阻塞 GUI。
        """
        all_items = []
        page_size = 500
        offset = 0
        while True:
            page = self._repo.get_assets(view_id, sort_by,
                                         offset=offset, limit=page_size)
            if not page:
                break
            all_items.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        with QMutexLocker(self._mutex):
            self._items = all_items
            self._cache.clear()

        self.data_loaded.emit(len(all_items))

    def reset(self):
        """清空数据，通常用于切换视图前"""
        with QMutexLocker(self._mutex):
            self._items.clear()
            self._cache.clear()

    @property
    def total_items(self) -> int:
        """资产总数（线程安全）"""
        with QMutexLocker(self._mutex):
            return len(self._items)

    @property
    def thumbnail_type(self) -> AssetImageType:
        """当前使用的缩略图尺寸类型（线程安全）"""
        with QMutexLocker(self._mutex):
            return self._thumbnail_type

    def set_thumbnail_type(self, new_type: AssetImageType):
        """
        切换缩略图尺寸类型，会清空内存缓存并通知 UI 刷新。
        忽略 ORIGINAL 类型。
        """
        if new_type == AssetImageType.ORIGINAL:
            return
        with QMutexLocker(self._mutex):
            if new_type == self._thumbnail_type:
                return
            self._thumbnail_type = new_type
            self._cache.clear()
        self.thumbnail_size_changed.emit()

    def get_thumbnail(self, index: int) -> QImage:
        """
        获取指定索引的缩略图（线程安全）。
        由 Cell 的工作线程调用。
        若不存在则异步请求生成，同时返回占位图。
        """
        # 1. 缓存命中（当前尺寸类型）
        with QMutexLocker(self._mutex):
            if index in self._cache:
                img = self._cache.pop(index)
                self._cache[index] = img   # LRU 移至末尾
                return img
            if index < 0 or index >= len(self._items):
                return self._create_placeholder(index)
            item = self._items[index]

        # 2. 根据当前尺寸类型获取对应字段的缩略图文件路径
        field_name = self._thumbnail_type.value  # 如 'thumb_path'
        thumb_path = getattr(item, field_name, None)
        if thumb_path and os.path.isfile(thumb_path):
            img = self._load_image(thumb_path)
            if not img.isNull():
                self._add_to_cache(index, img)
                return img

        # 3. 缩略图文件不存在，使用原图请求生成
        source_path = item.file_path   # ORIGINAL 对应的字段
        if source_path and os.path.isfile(source_path):
            self._thumbnail_gen.request(source_path, self._thumbnail_type.max_size)

        return self._create_placeholder(index)

    # ---------------------- 内部方法 ----------------------
    @Slot(str, int, QImage)
    def _on_thumbnail_ready(self, uri: str, size: int, img: QImage):
        """缩略图异步生成完成后的槽函数（主线程调用）"""
        # 查找对应的资产索引
        index = -1
        with QMutexLocker(self._mutex):
            for i, item in enumerate(self._items):
                if item.file_path and self._file_uri_matches(item.file_path, uri):
                    index = i
                    break
        if index < 0:
            return

        # 仅当尺寸与当前选择的类型一致时才缓存并通知
        with QMutexLocker(self._mutex):
            current_size = self._thumbnail_type.max_size
        if size != current_size:
            return

        if not img.isNull():
            self._add_to_cache(index, img)
            self.thumbnail_updated.emit(index)

    @staticmethod
    def _load_image(path: str) -> QImage:
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        return reader.read()

    @staticmethod
    def _create_placeholder(index: int) -> QImage:
        return image_provider(index)  # 已有的占位图生成器

    def _add_to_cache(self, index: int, img: QImage):
        with QMutexLocker(self._mutex):
            self._cache[index] = img
            while len(self._cache) > self._max_cache:
                self._cache.popitem(last=False)

    @staticmethod
    def _file_uri_matches(file_path: str, file_uri: str) -> bool:
        """比较本地绝对路径与 file:// URI 是否指向同一文件"""
        from urllib.parse import urlparse, unquote
        abs_path = os.path.abspath(file_path)
        parsed = urlparse(file_uri)
        uri_path = unquote(parsed.path)
        return os.path.abspath(uri_path) == abs_path
