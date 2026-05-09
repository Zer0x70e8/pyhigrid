#
""""""

import hashlib
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING
import sqlite3

from PIL import Image, ExifTags
from PIL.Image import Resampling

from pyhigrid.schemas.enums import AssetImageType
from pyhigrid.schemas.constants import UUID_UNORGANIZED, UUID_ALL_PHOTOS

if TYPE_CHECKING:
    from pyhigrid.db import Database  # noqa

# 支持的文件扩展名
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.tif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# 缩略图尺寸
THUMB_SMALL = (AssetImageType.THUMB_SMALL.max_size, ) * 2  # type: tuple[int, int]
THUMB_MEDIUM = (AssetImageType.THUMB_MEDIUM.max_size, ) * 2  # type: tuple[int, int]
THUMB_LARGE = (AssetImageType.THUMB_LARGE.max_size, ) * 2  # type: tuple[int, int]
THUMB_ORIGINAL = AssetImageType.ORIGINAL.max_size  # type: None

# 内置相簿 UUID
ALBUM_ALL_PHOTOS = UUID_ALL_PHOTOS  # "00000000-0000-0000-0000-000000000003"
ALBUM_UNORGANIZED = UUID_UNORGANIZED  # "00000000-0000-0000-0000-000000000005"


class ImporterRepo:
    """负责将媒体文件导入数据库的仓库类"""

    def __init__(self, db: 'Database', thumb_dir: Path):
        self.db = db
        self.thumb_dir = Path(thumb_dir)
        self.thumb_dir.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None

    def _connect(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = self.db.connect()
        return self.conn

    @staticmethod
    def _compute_file_hash(file_path: Path) -> str:
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _get_asset_type(ext: str) -> str:
        ext = ext.lower()
        if ext in IMAGE_EXTENSIONS:
            return 'image'
        return 'video'

    @staticmethod
    def _get_mime_type(ext: str) -> str:
        mapping = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png', '.bmp': 'image/bmp',
            '.gif': 'image/gif', '.webp': 'image/webp',
            '.tiff': 'image/tiff', '.tif': 'image/tiff',
            '.mp4': 'video/mp4', '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo', '.mkv': 'video/x-matroska',
            '.webm': 'video/webm', '.flv': 'video/x-flv',
            '.wmv': 'video/x-ms-wmv',
        }
        return mapping.get(ext.lower(), 'application/octet-stream')

    def _extract_exif(self, file_path: Path) -> dict:
        info = {
            'taken_at': self._get_file_time_as_iso(file_path),
            'width': 0,
            'height': 0,
            'city': None,
            'exif_json': None,
        }
        # noinspection PyBroadException
        try:
            img = Image.open(file_path)
            info['width'], info['height'] = img.size

            exif_data = img.getexif()
            if exif_data:
                exif = {}
                for tag, value in exif_data.items():
                    name = ExifTags.TAGS.get(tag, tag)
                    exif[name] = value
                info['exif_json'] = str(exif)

                date_str = exif.get('DateTimeOriginal')
                if date_str:
                    try:
                        dt = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                        info['taken_at'] = dt.strftime('%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        pass
        except Exception:
            pass
        return info

    @staticmethod
    def _get_file_time_as_iso(file_path: Path) -> str:
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%dT%H:%M:%S')

    def _generate_thumbnails(self, file_path: Path,
                             asset_uuid: str,
                             mime_type: str
                             ) -> Optional[dict]:
        if not mime_type.startswith('image/'):
            return None

        # noinspection PyBroadException
        try:
            img = Image.open(file_path)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')

            paths = {}
            # 小图
            small_path = self.thumb_dir / f'{asset_uuid}_thumb_small.jpg'
            self._save_thumbnail(img, THUMB_SMALL, small_path)
            paths['thumb_small_path'] = str(small_path)

            # 中图
            medium_path = self.thumb_dir / f'{asset_uuid}_thumb_medium.jpg'
            self._save_thumbnail(img, THUMB_MEDIUM, medium_path)
            paths['thumb_medium_path'] = str(medium_path)

            # 大图
            large_path = self.thumb_dir / f'{asset_uuid}_thumb_large.jpg'
            self._save_thumbnail(img, THUMB_LARGE, large_path)
            paths['thumb_path'] = str(large_path)

            return paths
        except Exception:
            return None

    @staticmethod
    def _save_thumbnail(img: Image.Image, size: tuple[int, int], dest: Path):
        """保存缩略图，不放大"""
        img.thumbnail(size, Resampling.LANCZOS)
        img.save(dest, 'JPEG', quality=85)

    def _get_builtin_album_ids(self) -> dict:
        cur = self._connect().execute(
            "SELECT uuid, id FROM albums WHERE uuid IN (?, ?)",
            (ALBUM_ALL_PHOTOS, ALBUM_UNORGANIZED)
        )
        return {row['uuid']: row['id'] for row in cur.fetchall()}

    def _asset_exists_by_hash(self, file_hash: str) -> Optional[dict]:
        cur = self._connect().execute(
            "SELECT id, uuid, is_deleted FROM assets WHERE file_hash = ?",
            (file_hash,)
        )
        return cur.fetchone()

    def import_asset(self, file_path: Path, thumb_paths: Optional[dict] = None) -> bool:
        try:
            file_path = file_path.resolve()
            ext = file_path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                return False

            file_hash = self._compute_file_hash(file_path)
            existing = self._asset_exists_by_hash(file_hash)
            if existing and not existing['is_deleted']:
                return False

            exif_info = self._extract_exif(file_path)
            asset_uuid = str(uuid.uuid4())
            mime_type = self._get_mime_type(ext)
            file_size = file_path.stat().st_size

            # 缩略图：外部优先，否则内置生成
            if thumb_paths is not None:
                thumb_path = thumb_paths.get('thumb_path')
                thumb_small = thumb_paths.get('thumb_small_path')
                thumb_medium = thumb_paths.get('thumb_medium_path')
                if thumb_path and not Path(thumb_path).exists():
                    thumb_path = None
                if thumb_small and not Path(thumb_small).exists():
                    thumb_small = None
                if thumb_medium and not Path(thumb_medium).exists():
                    thumb_medium = None
            else:
                paths = self._generate_thumbnails(file_path, asset_uuid, mime_type)
                if paths:
                    thumb_path = paths.get('thumb_path')
                    thumb_small = paths.get('thumb_small_path')
                    thumb_medium = paths.get('thumb_medium_path')
                else:
                    thumb_path = None
                    thumb_small = None
                    thumb_medium = None

            if existing and existing['is_deleted']:
                self._connect().execute(
                    """UPDATE assets SET
                        uuid = ?, file_path = ?, thumb_path = ?, thumb_small_path = ?,
                        thumb_medium_path = ?, original_name = ?, mime_type = ?,
                        file_hash = ?, file_size = ?, width = ?, height = ?,
                        taken_at = ?, city = ?, exif_json = ?,
                        is_deleted = 0, deleted_at = NULL,
                        modified_at = strftime('%Y-%m-%dT%H:%M:%f', 'now')
                     WHERE id = ?""",
                    (asset_uuid, str(file_path), thumb_path, thumb_small,
                     thumb_medium, file_path.name, mime_type,
                     file_hash, file_size, exif_info['width'], exif_info['height'],
                     exif_info['taken_at'], exif_info['city'], exif_info['exif_json'],
                     existing['id'])
                )
                asset_id = existing['id']
            else:
                cur = self._connect().execute(
                    """INSERT INTO assets
                        (uuid, file_path, thumb_path, thumb_small_path, thumb_medium_path,
                         original_name, mime_type, file_hash, file_size, width, height,
                         taken_at, city, exif_json)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (asset_uuid, str(file_path), thumb_path, thumb_small,
                     thumb_medium, file_path.name, mime_type,
                     file_hash, file_size, exif_info['width'], exif_info['height'],
                     exif_info['taken_at'], exif_info['city'], exif_info['exif_json'])
                )
                asset_id = cur.lastrowid

            # 默认相簿关联
            album_ids = self._get_builtin_album_ids()
            for album_type in (ALBUM_ALL_PHOTOS, ALBUM_UNORGANIZED):
                alb_id = album_ids.get(album_type)
                if alb_id:
                    self._connect().execute(
                        """INSERT OR IGNORE INTO album_assets
                            (album_id, asset_id, asset_taken_at)
                         VALUES (?, ?, ?)""",
                        (alb_id, asset_id, exif_info['taken_at'])
                    )
            self._connect().commit()
            return True
        except Exception as e:
            print(f"Error importing {file_path}: {e}")
            return False

    def import_directory(self, directory: Path, recursive: bool = True) -> int:
        count = 0
        pattern = '**/*' if recursive else '*'
        for file_path in Path(directory).glob(pattern):
            if file_path.is_file():
                if self.import_asset(file_path):
                    count += 1
        return count
