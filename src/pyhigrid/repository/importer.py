#
"""
导入专用仓库 (ImportRepository) —— 面向后台导入服务

职责：
    - 接受文件原始信息（FileImportInfo 或字典），将资产安全写入数据库。
    - 自动将新资产关联到系统默认虚拟相簿（ALL_PHOTOS, UNORGANIZED）。
    - 支持调用方指定额外的目标相簿 UUID 列表，实现特殊场景导入（如截图、下载等）。
    - 批量导入提供事务原子性。

安全与一致性：
    - 全部 SQL 参数化。
    - 活跃哈希唯一索引 + 主动查重 + 并发冲突安全处理。
    - 虚拟相簿使用 ON CONFLICT 自动恢复软删除。
    - 关联使用主键冲突忽略。
    - 严格过滤允许写入的字段列表。
"""

import dataclasses
from typing import List, Optional, Dict, Any, Union
from sqlite3 import IntegrityError

from pyhigrid.domain.enums import BaseAlbum
from pyhigrid.domain.entities import FileImportInfo
from .base import BaseRepository


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
    # 公共导入方法 —— 服务层直接调用这两个
    # ------------------------------------------------------------------

    def import_file(self,
                    file_info: Union['FileImportInfo', Dict[str, Any]],
                    target_album_uuids: Optional[List[str]] = None) -> Optional[int]:
        """
        导入单个文件（原始信息）。

        :param file_info: 文件元信息，可以是 FileImportInfo 数据类或字典。
        :param target_album_uuids: 除默认虚拟相簿外，额外需要关联的相簿 UUID 列表。
        :return: 新导入资产的 asset_id；若文件重复则返回 None。
        """
        data = self._to_dict(file_info)
        self._validate_required(data)
        return self._import_single(data, target_album_uuids or [])

    def batch_import_files(self,
                           files: List[Union['FileImportInfo', Dict[str, Any]]],
                           target_album_uuids: Optional[List[str]] = None) -> Dict[str, int]:
        """
        批量导入文件（单一事务）。

        行为：所有文件在同一个事务中处理。
        重复文件（根据 file_hash 已存在或本次冲突）将被跳过，不中断事务。
        若遇到非哈希冲突的数据库错误，则整个事务回滚并抛出异常。

        :param files: 文件信息列表。
        :param target_album_uuids: 额外关联的相簿 UUID 列表。
        :return: {'inserted': int, 'skipped': int}
        """
        uuids = target_album_uuids or []
        data_list = [self._to_dict(f) for f in files]

        inserted = 0
        skipped = 0
        conn = self._db.connect()
        try:
            # 1. 确保所有需要关联的相簿（默认 + 额外）都已存在，获取 album_id
            album_ids = self._resolve_album_ids_in_conn(conn, uuids)

            for data in data_list:
                # 2. 主动去重（性能优化，减少触发唯一约束的可能）
                exists = conn.execute(
                    "SELECT 1 FROM assets WHERE file_hash = ? AND is_deleted = 0",
                    (data["file_hash"],)
                ).fetchone()
                if exists:
                    skipped += 1
                    continue

                # 3. 插入资产（捕获哈希冲突，其它异常向外抛出）
                try:
                    asset_id = self._insert_asset_in_conn(conn, data)
                except IntegrityError as e:
                    # 判断是否仅由 file_hash 唯一约束引发
                    if "file_hash" in str(e):
                        skipped += 1
                        continue
                    raise  # 其他完整性错误（如非空约束）直接抛出，导致事务回滚

                # 4. 关联到所有目标相簿（默认 + 额外）
                taken = data.get("taken_at")
                for alb_id in album_ids:
                    try:
                        conn.execute(
                            "INSERT INTO album_assets (album_id, asset_id, asset_taken_at) VALUES (?, ?, ?)",
                            (alb_id, asset_id, taken)
                        )
                    except IntegrityError:
                        pass  # 已存在关联，正常忽略
                inserted += 1

            conn.commit()
            return {"inserted": inserted, "skipped": skipped}
        except Exception:
            conn.rollback()
            raise

    # ------------------------------------------------------------------
    # 内部原子操作（基于连接）
    # ------------------------------------------------------------------

    def _import_single(self,
                       data: Dict[str, Any],
                       extra_uuids: List[str]) -> Optional[int]:
        """单文件导入的完整流程（自动管理事务）。"""
        conn = self._db.connect()
        try:
            # 主动去重
            if conn.execute(
                "SELECT 1 FROM assets WHERE file_hash = ? AND is_deleted = 0",
                (data["file_hash"],)
            ).fetchone():
                return None

            # 插入资产（捕获可能的并发冲突）
            try:
                asset_id = self._insert_asset_in_conn(conn, data)
            except IntegrityError as e:
                if "file_hash" in str(e):
                    return None   # 并发插入同一哈希，视为重复
                raise

            # 关联相簿
            album_ids = self._resolve_album_ids_in_conn(conn, extra_uuids)
            taken = data.get("taken_at")
            for alb_id in album_ids:
                try:
                    conn.execute(
                        "INSERT INTO album_assets (album_id, asset_id, asset_taken_at) VALUES (?, ?, ?)",
                        (alb_id, asset_id, taken)
                    )
                except IntegrityError:
                    pass
            conn.commit()
            return asset_id
        except Exception:
            conn.rollback()
            raise

    def _insert_asset_in_conn(self, conn, data: Dict[str, Any]) -> int:
        """在给定连接上插入一条资产记录，返回 asset_id。不捕获异常。"""
        params = self._build_params(data)
        columns = ", ".join(params.keys())
        placeholders = ", ".join("?" for _ in params)
        cursor = conn.execute(
            f"INSERT INTO assets ({columns}) VALUES ({placeholders})",
            tuple(params.values())
        )
        return cursor.lastrowid

    # ------------------------------------------------------------------
    # 相簿 ID 解析（确保存在并返回 ID 列表）
    # ------------------------------------------------------------------

    def _resolve_album_ids_in_conn(self, conn, extra_uuids: List[str]) -> List[int]:
        """
        解析相簿 ID 集合 = 默认虚拟相簿 + 额外指定相簿。
        会自动确保默认虚拟相簿存在（必要时恢复软删除），
        但对额外 UUID 仅查询（不负责创建，调用方需保证其存在）。
        找不到的额外相簿将被静默忽略（可考虑后续增加日志或严格模式）。
        """
        album_ids = []
        # 默认虚拟相簿：插入或恢复软删除状态
        for base in self.DEFAULT_VIRTUAL_ALBUMS:
            conn.execute(
                """INSERT INTO albums (uuid, title, album_type, is_deleted)
                   VALUES (?, ?, ?, 0)
                   ON CONFLICT(uuid) DO UPDATE SET is_deleted = 0""",
                (str(base.uuid), base.label, base.album_type.value)
            )
            row = conn.execute(
                "SELECT id FROM albums WHERE uuid = ? AND is_deleted = 0",
                (str(base.uuid),)
            ).fetchone()
            if row:
                album_ids.append(row["id"])

        # 额外相簿（只查询，不创建）
        for uuid_str in extra_uuids:
            row = conn.execute(
                "SELECT id FROM albums WHERE uuid = ? AND is_deleted = 0",
                (uuid_str,)
            ).fetchone()
            if row:
                album_ids.append(row["id"])
        return album_ids

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(file_info) -> Dict[str, Any]:
        """将 FileImportInfo 或字典统一转换为字典。"""
        if isinstance(file_info, FileImportInfo):
            # 直接使用 dataclasses.asdict 转换整个实例
            return dataclasses.asdict(file_info)
        elif isinstance(file_info, dict):
            # 简单返回，调用方可自行保证字典字段完整
            return file_info
        else:
            raise TypeError("file_info must be a FileImportInfo instance or a dict")

    @classmethod
    def _validate_required(cls, data: Dict[str, Any]):
        """校验导入必需的字段，缺失时抛出 ValueError。"""
        required_fields = ["uuid", "file_path", "file_hash", "original_name", "mime_type"]
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Missing required field for import: {field}")

    @classmethod
    def _build_params(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """从原始信息中提取允许 INSERT 的字段，并补全默认值。"""
        params = {k: v for k, v in data.items() if k in cls.ASSET_INSERT_FIELDS}
        params.setdefault("is_favorite", 0)
        return params
