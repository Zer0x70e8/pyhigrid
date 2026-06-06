#
"""
导入专用仓库 (ImportRepository) —— 面向后台导入服务 (优化版)
"""
import dataclasses
from typing import List, Optional, Dict, Any, Union
from sqlite3 import IntegrityError

from pyhigrid.domain.enums import BaseAlbum
from pyhigrid.domain.entities import FileImportInfo
from .base import BaseRepository
from .utils.sql_helpers import placeholders, filter_dict


@dataclasses.dataclass
class BatchImportResult:
    """批量导入结果"""
    inserted: int
    skipped: int


class ImportRepository(BaseRepository):
    # 允许 INSERT 的字段（与 assets 表对应，不含自动生成的 id, created_at 等）
    ASSET_INSERT_FIELDS = {
        "uuid", "file_path", "thumb_path", "thumb_small_path", "thumb_medium_path",
        "original_name", "mime_type", "file_hash", "file_size", "width", "height",
        "taken_at", "city", "exif_json", "is_favorite"
    }

    # 默认导入时必须关联的虚拟相簿
    DEFAULT_VIRTUAL_ALBUMS = [BaseAlbum.ALL_PHOTOS, BaseAlbum.UNORGANIZED]

    # ------------------------------------------------------------------
    # 公共导入方法
    # ------------------------------------------------------------------

    def import_file(self,
                    file_info: Union['FileImportInfo', Dict[str, Any]],
                    target_album_uuids: Optional[List[str]] = None) -> Optional[int]:
        """
        导入单个文件，返回新资产的 asset_id；文件重复则返回 None。
        """
        data = self._to_dict(file_info)
        self._validate_required(data)

        with self._transaction() as conn:
            # 1. 主动去重
            if conn.execute(
                "SELECT 1 FROM assets WHERE file_hash = ? AND is_deleted = 0",
                (data["file_hash"],)
            ).fetchone():
                self.logger.info("跳过重复文件: %s", data.get("original_name"))
                return None

            # 2. 解析相簿
            album_ids = self._resolve_album_ids_in_conn(conn, target_album_uuids or [])

            # 3. 执行导入
            try:
                asset_id = self._import_asset_in_conn(conn, data, album_ids)
            except IntegrityError as e:
                if "file_hash" in str(e):
                    self.logger.info("并发冲突，跳过重复文件: %s", data.get("original_name"))
                    return None
                raise

            return asset_id

    def batch_import_files(self,
                           files: List[Union['FileImportInfo', Dict[str, Any]]],
                           target_album_uuids: Optional[List[str]] = None
                           ) -> BatchImportResult:
        """
        批量导入文件，单一事务。
        重复文件自动跳过，其他数据库错误导致全量回滚。
        """
        uuids = target_album_uuids or []
        data_list = [self._to_dict(f) for f in files]
        for idx, data in enumerate(data_list, start=1):
            try:
                self._validate_required(data)
            except ValueError as e:
                raise ValueError(f"第 {idx} 个文件缺少必需字段: {e}") from e

        with self._transaction() as conn:
            # 1. 构建输入哈希集合，并一次性查询已存在的哈希
            input_hashes = {d["file_hash"] for d in data_list}
            existing_hashes = set()
            if input_hashes:
                query = (f"SELECT file_hash FROM assets WHERE file_hash "
                         f"IN ({placeholders(len(input_hashes))}) AND is_deleted = 0")
                rows = conn.execute(query, tuple(input_hashes)).fetchall()
                existing_hashes = {row["file_hash"] for row in rows}

            # 2. 根据已存在哈希过滤待导入数据，同时处理列表内部重复
            seen_hashes = set()
            filtered_data = []
            skipped = 0
            for d in data_list:
                h = d["file_hash"]
                if h in existing_hashes or h in seen_hashes:
                    skipped += 1
                    self.logger.debug("跳过重复文件: %s", d.get("original_name"))
                    continue
                seen_hashes.add(h)
                filtered_data.append(d)

            # 3. 解析相簿 ID（默认 + 额外）
            album_ids = self._resolve_album_ids_in_conn(conn, uuids)

            # 4. 逐条插入并关联
            inserted = 0
            for data in filtered_data:
                try:
                    self._import_asset_in_conn(conn, data, album_ids)
                    inserted += 1
                except IntegrityError as e:
                    if "file_hash" in str(e):
                        skipped += 1
                        self.logger.debug("并发冲突，跳过文件: %s", data.get("original_name"))
                        continue
                    raise  # 其他约束错误导致事务回滚

            return BatchImportResult(inserted=inserted, skipped=skipped)

    # ------------------------------------------------------------------
    # 内部原子操作
    # ------------------------------------------------------------------

    def _import_asset_in_conn(self, conn, data: Dict[str, Any], album_ids: List[int]) -> int:
        """
        在给定连接上完成资产插入及相簿关联，返回 asset_id。
        不处理重复冲突，调用方负责捕获 IntegrityError。
        """
        asset_id = self._insert_asset_in_conn(conn, data)
        taken = data.get("taken_at")
        for alb_id in album_ids:
            try:
                conn.execute(
                    "INSERT INTO album_assets (album_id, asset_id, asset_taken_at) VALUES (?, ?, ?)",
                    (alb_id, asset_id, taken)
                )
            except IntegrityError:
                pass  # 关联已存在时忽略
        return asset_id

    def _insert_asset_in_conn(self, conn, data: Dict[str, Any]) -> int:
        """插入资产行并返回 lastrowid。"""
        allowed = filter_dict(data, self.ASSET_INSERT_FIELDS)
        # 为 is_favorite 设置默认值
        allowed.setdefault("is_favorite", 0)

        columns = list(allowed.keys())
        values = list(allowed.values())
        sql = f"INSERT INTO assets ({', '.join(columns)}) VALUES ({placeholders(len(columns))})"
        cursor = conn.execute(sql, values)
        return cursor.lastrowid

    # ------------------------------------------------------------------
    # 相簿 ID 解析
    # ------------------------------------------------------------------

    def _resolve_album_ids_in_conn(self, conn, extra_uuids: List[str]) -> List[int]:
        """
        返回所有需要关联的相簿 id 列表：
        - 默认虚拟相簿：确保存在并返回其 id
        - 额外指定相簿：仅查询，不存在则静默忽略
        """
        album_ids = []

        # 1. 默认虚拟相簿（批量查询，按需创建）
        default_uuids = [str(alb.uuid) for alb in self.DEFAULT_VIRTUAL_ALBUMS]
        # 查询已存在且未删除的
        rows = conn.execute(
            f"SELECT uuid, id FROM albums WHERE uuid IN ({placeholders(len(default_uuids))}) AND is_deleted = 0",
            default_uuids
        ).fetchall()
        existing_map = {row["uuid"]: row["id"] for row in rows}

        for alb in self.DEFAULT_VIRTUAL_ALBUMS:
            uid = str(alb.uuid)
            if uid in existing_map:
                album_ids.append(existing_map[uid])
            else:
                # 不存在或被软删除 -> 创建/恢复
                conn.execute(
                    """INSERT INTO albums (uuid, title, album_type, is_deleted)
                       VALUES (?, ?, ?, 0)
                       ON CONFLICT(uuid) DO UPDATE SET is_deleted = 0""",
                    (uid, alb.label, alb.album_type.value)
                )
                # 重新获取 id
                new_id = conn.execute(
                    "SELECT id FROM albums WHERE uuid = ?", (uid,)
                ).fetchone()["id"]
                album_ids.append(new_id)

        # 2. 额外相簿（仅查询）
        if extra_uuids:
            rows = conn.execute(
                f"SELECT id FROM albums WHERE uuid IN ({placeholders(len(extra_uuids))}) AND is_deleted = 0",
                extra_uuids
            ).fetchall()
            album_ids.extend(row["id"] for row in rows)

        return album_ids

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(file_info) -> Dict[str, Any]:
        """统一转换为字典。"""
        if isinstance(file_info, FileImportInfo):
            return dataclasses.asdict(file_info)
        if isinstance(file_info, dict):
            return file_info
        raise TypeError("file_info 必须为 FileImportInfo 实例或字典")

    @classmethod
    def _validate_required(cls, data: Dict[str, Any]):
        """校验导入必需字段。"""
        required_fields = ["uuid", "file_path", "file_hash", "original_name", "mime_type"]
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"导入数据缺少必需字段: {field}")
