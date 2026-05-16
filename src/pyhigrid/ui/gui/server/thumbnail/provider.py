#
""""""

import os
from typing import List, Dict, OrderedDict, Optional

from PySide6.QtCore import QObject, QMutex, QMutexLocker, Qt
from PySide6.QtGui import QImage, QImageReader

from pyhigrid.schemas.enums import AssetImageType, AlbumAssetSortOption
from ...widget.virtual_scroll.utils import image_provider


class AssetImageProvider(QObject):
    """
    为虚拟滚动组件提供缩略图的异步数据源。
    所有会在工作线程调用的方法都设计为线程安全（除 GUI 回调）。
    """

    def __init__(self, album_repo, thumbnail_type: AssetImageType = AssetImageType.THUMB_SMALL):
        super().__init__()
        self._repo = album_repo
        self._thumbnail_type = thumbnail_type  # 决定使用哪个缩略图字段及尺寸
        self._items: List[Dict] = []  # 缓存的全量资产简要信息
        self._mutex = QMutex()
        self._cache: OrderedDict[int, QImage] = OrderedDict()
        self._max_cache = 200  # 最多缓存 200 张缩略图

    # ---------- 数据加载 ----------
    def load_album(self, album_id: int, sort_by: AlbumAssetSortOption = AlbumAssetSortOption.TAKEN_AT):
        """加载指定相簿的全部资产 ID 和路径信息（工作线程或主线程均可，完成后更新列表）"""
        # 这里调用 repo 获取全量（对于超大相簿，repo 可能需要调整，见下文说明）
        assets = self._repo.get_album_assets(album_id, sort_by, limit=0)  # 假设 limit=0 返回全部
        # 如果 repo 不支持全量，可改为循环分页拉取
        new_items = []
        for a in assets:
            new_items.append({
                'id': a['id'],
                'file_path': a['file_path'],
                'thumb_small': a.get('thumb_small_path'),
                'thumb_medium': a.get('thumb_medium_path'),
                'thumb_large': a.get('thumb_path'),
                'mime_type': a['mime_type'],
                'width': a['width'],
                'height': a['height']
            })
        with QMutexLocker(self._mutex):
            self._items = new_items
            self._cache.clear()
        # 通知外界总数变化（主线程通过信号，但可直接由调用方负责刷新 UI）
        # 我们暴露 total_items 属性供虚拟滚动查询

    @property
    def total_items(self) -> int:
        with QMutexLocker(self._mutex):
            return len(self._items)

    # ---------- 缩略图生成（工作线程调用） ----------
    def get_thumbnail(self, index: int) -> QImage:
        """根据全局索引生成/加载缩略图。线程安全。"""
        # 1. 查缓存
        with QMutexLocker(self._mutex):
            if index in self._cache:
                # 移动到最后（LRU）
                img = self._cache.pop(index)
                self._cache[index] = img
                return img

            if index < 0 or index >= len(self._items):
                return self._create_placeholder(index)

            item = self._items[index]

        # 2. 优先使用已存在的缩略图文件
        thumb_path = self._get_thumb_path(item)
        if thumb_path and os.path.isfile(thumb_path):
            img = self._load_image(thumb_path)
            if not img.isNull():
                self._add_to_cache(index, img)
                return img

        # 3. 回退：用原图实时生成缩略图（不阻塞 UI，已在工作线程）
        #    这里可以根据 mime_type 决定是否只处理图片
        if item['file_path'] and os.path.isfile(item['file_path']):
            img = self._generate_thumbnail_from_original(item['file_path'])
            if not img.isNull():
                self._add_to_cache(index, img)
                return img

        # 4. 完全失败：返回占位图
        return self._create_placeholder(index)

    def _get_thumb_path(self, item: Dict) -> Optional[str]:
        """根据当前缩略图类型返回可能存在的文件路径"""
        if self._thumbnail_type == AssetImageType.THUMB_SMALL:
            return item['thumb_small']
        elif self._thumbnail_type == AssetImageType.THUMB_MEDIUM:
            return item['thumb_medium']
        elif self._thumbnail_type == AssetImageType.THUMB_LARGE:
            return item['thumb_large']
        return None

    @staticmethod
    def _load_image(path: str) -> QImage:
        """安全读取图像文件（工作线程可用）"""
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        return reader.read()

    def _generate_thumbnail_from_original(self, original_path: str) -> QImage:
        """使用原图生成指定尺寸的缩略图"""
        max_size = self._thumbnail_type.max_size
        if max_size is None:
            max_size = 256  # 原图类型不应该走这里，但保留 fallback
        reader = QImageReader(original_path)
        reader.setAutoTransform(True)
        # 根据原图尺寸计算等比缩放
        orig_size = reader.size()
        if orig_size.isValid():
            scaled = orig_size.scaled(max_size, max_size, Qt.KeepAspectRatio)
            reader.setScaledSize(scaled)
        return reader.read()

    def _add_to_cache(self, index: int, img: QImage):
        with QMutexLocker(self._mutex):
            self._cache[index] = img
            while len(self._cache) > self._max_cache:
                self._cache.popitem(last=False)  # 删除最久未用

    @staticmethod
    def _create_placeholder(index: int) -> QImage:
        """生成一个显示索引数字的占位图（image_provider）"""
        # 直接调用你已有的 image_provider 函数，或者内联简单绘制
        return image_provider(index)
