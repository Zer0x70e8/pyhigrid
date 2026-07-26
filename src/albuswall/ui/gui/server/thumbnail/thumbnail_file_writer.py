#
"""
缩略图文件写入器 —— 在子进程中生成多尺寸缩略图并直接写盘。
不依赖 Qt，可被任何服务层调用。
"""

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict

from PIL import Image, ImageOps

from albuswall.domain.constants import THUMB_SIZE_SMALL, THUMB_SIZE_MEDIUM, THUMB_SIZE_LARGE

PRESET_SIZES = {
    "small": THUMB_SIZE_SMALL,
    "medium": THUMB_SIZE_MEDIUM,
    "large": THUMB_SIZE_LARGE,
}

def _generate_and_save(
    source_path: str,
    base_dir: str,
    uuid: str,
    sizes: Dict[str, int]
) -> Dict[str, str]:
    """
    子进程任务：从原图生成多种尺寸的缩略图并保存。
    返回 {"small": path, "medium": path, "large": path}，
    若处理失败则对应值为空字符串。
    """
    result = {key: "" for key in sizes}
    try:
        # 创建目标子目录（若不存在）
        subdir = os.path.join(base_dir, uuid[:2])
        os.makedirs(subdir, exist_ok=True)

        with Image.open(source_path) as img:
            img.load()
            for label, size in sizes.items():
                try:
                    thumb = ImageOps.fit(img, (size, size), method=Image.Resampling.LANCZOS)
                    # 文件名加入尺寸标识，便于管理
                    filename = f"{uuid}_{label}.png"
                    save_path = os.path.join(subdir, filename)
                    thumb.save(save_path, format="PNG")
                    result[label] = save_path
                except Exception:
                    # 单个尺寸失败不影响其他尺寸
                    result[label] = ""
    except Exception:
        # 整个原图处理失败，所有结果为空
        pass
    return result


class ThumbnailFileWriter:
    """
    在进程池中批量生成缩略图文件。
    使用方式：
        writer = ThumbnailFileWriter(max_workers=4)
        paths = writer.process(asset_uuid, source_path, thumb_base_dir)
        -> {"small": "/...uuid_small.png", ...}
    """

    def __init__(self, max_workers: int = 4):
        self._executor = ProcessPoolExecutor(max_workers=max_workers)
        self._max_workers = max_workers

    def process(self, uuid: str, source_path: str,
                thumb_base_dir: str) -> Dict[str, str]:
        """同步生成单个资产的所有预设缩略图（适用于批量任务）。"""
        future = self._executor.submit(
            _generate_and_save,
            source_path, thumb_base_dir, uuid, PRESET_SIZES
        )
        return future.result()

    def process_batch(self, tasks: Dict[str, str],
                      thumb_base_dir: str) -> Dict[str, Dict[str, str]]:
        """
        批量处理，返回 {uuid: {"small": path, ...}}。
        """
        futures = {}
        with ProcessPoolExecutor(max_workers=self._max_workers) as executor:
            for uuid, path in tasks.items():
                future = executor.submit(
                    _generate_and_save,
                    path, thumb_base_dir, uuid, PRESET_SIZES
                )
                futures[future] = uuid

        results = {}
        for future in as_completed(futures):
            uuid = futures[future]
            try:
                results[uuid] = future.result()
            except Exception:
                results[uuid] = {k: "" for k in PRESET_SIZES}
        return results

    def shutdown(self):
        self._executor.shutdown(wait=False)
