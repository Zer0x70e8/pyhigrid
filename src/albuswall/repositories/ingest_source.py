#
""""""

import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseRepository
from albuswall.domain.constants import IngestSource
from albuswall.domain.entities import IngestSourceEntity

BOOL_FIELDS = IngestSource.BOOL_FIELDS
JSON_FIELDS = IngestSource.JSON_FIELDS
ALLOWED_FIELDS = IngestSource.ALLOWED_FIELDS

logger = logging.getLogger("albuswall.ingest_source_repository")


class IngestSourceRepository(BaseRepository):
    def create(self, **kwargs: Any) -> int:
        """Insert a new ingest source configuration, returns the new id."""
        logger.debug("Creating ingest source with data: %s", kwargs)

        if "title" not in kwargs or "source_path" not in kwargs:
            error_msg = "Both 'title' and 'source_path' are required to create an ingest source"
            logger.error(error_msg)
            raise ValueError(error_msg)

        insert_data = {k: v for k, v in kwargs.items() if k in ALLOWED_FIELDS}
        if not insert_data:
            error_msg = f"No valid fields provided for insert: {insert_data}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Use SQLite's CURRENT_TIMESTAMP instead of a string literal
        insert_data.setdefault("created_at", "CURRENT_TIMESTAMP")
        insert_data.setdefault("modified_at", "CURRENT_TIMESTAMP")

        db_data = self._to_db_row(insert_data)

        # Security: ensure all column names are from the allowed set
        for col in db_data.keys():
            if col not in ALLOWED_FIELDS:
                error_msg = f"Invalid column name '{col}' detected during insert"
                logger.error(error_msg)
                raise ValueError(error_msg)

        columns = ", ".join(db_data.keys())
        placeholders = ", ".join(["?"] * len(db_data))
        query = f"INSERT INTO ingest_source ({columns}) VALUES ({placeholders})"

        try:
            with self._transaction() as conn:
                cursor = conn.execute(query, tuple(db_data.values()))
                new_id = cursor.lastrowid
        except Exception as e:
            logger.error("Failed to create ingest source: %s", e)
            raise

        logger.info("Created ingest source with id: %d", new_id)
        assert isinstance(new_id, int)
        return new_id

    def update(self, source_id: int, **kwargs: Any) -> bool:
        """Update fields of a record, returns True if any row was modified."""
        logger.debug("Updating ingest source id=%s with data: %s", source_id, kwargs)

        update_data = {
            k: v
            for k, v in kwargs.items()
            if k in ALLOWED_FIELDS and v is not None
        }
        if not update_data:
            logger.debug("No valid fields to update for source id=%s", source_id)
            return False

        db_data = self._to_db_row(update_data)

        # Security: ensure all column names are from the allowed set
        for col in db_data.keys():
            if col not in ALLOWED_FIELDS:
                error_msg = f"Invalid column name '{col}' detected during update"
                logger.error(error_msg)
                raise ValueError(error_msg)

        set_clause = ", ".join([f"{key} = ?" for key in db_data.keys()])
        set_clause += ", modified_at = CURRENT_TIMESTAMP"

        query = f"UPDATE ingest_source SET {set_clause} WHERE id = ?"
        params = list(db_data.values()) + [source_id]

        try:
            with self._transaction() as conn:
                cursor = conn.execute(query, params)
                success = cursor.rowcount > 0
        except Exception as e:
            logger.error("Failed to update ingest source id=%s: %s", source_id, e)
            raise

        if success:
            logger.info("Updated ingest source id=%s", source_id)
        else:
            logger.warning("No rows updated for ingest source id=%s", source_id)
        return success

    def delete(self, source_id: int) -> bool:
        """Delete a record, returns True if successful."""
        logger.debug("Deleting ingest source id=%s", source_id)

        try:
            with self._transaction() as conn:
                cursor = conn.execute("DELETE FROM ingest_source WHERE id = ?", (source_id,))
                success = cursor.rowcount > 0
        except Exception as e:
            logger.error("Failed to delete ingest source id=%s: %s", source_id, e)
            raise

        if success:
            logger.info("Deleted ingest source id=%s", source_id)
        else:
            logger.warning("No rows deleted for ingest source id=%s", source_id)
        return success

    def exists(self, source_id: int) -> bool:
        """Check if a record with the given id exists."""
        row = self._fetchone("SELECT 1 FROM ingest_source WHERE id = ?", (source_id,))
        exists = row is not None
        logger.debug("Existence check for ingest source id=%s: %s", source_id, exists)
        return exists

    # Query
    def get_by_id(self, source_id: int) -> Optional[IngestSourceEntity]:
        """Get an entity by primary key, or None if not found."""
        logger.debug("Fetching ingest source by id=%s", source_id)
        row = self._fetchone("SELECT * FROM ingest_source WHERE id = ?", (source_id,))
        if row is None:
            logger.debug("No ingest source found with id=%s", source_id)
            return None
        entity = self._row_to_entity(dict(row))
        logger.debug("Found ingest source: %s", entity)
        return entity

    def get_all(self) -> List[IngestSourceEntity]:
        """Get all ingest source entities ordered by id."""
        logger.debug("Fetching all ingest sources")
        rows = self._fetchall("SELECT * FROM ingest_source ORDER BY id")
        if rows is None:
            logger.debug("No ingest sources found")
            return []
        entities = [self._row_to_entity(dict(row)) for row in rows]
        logger.debug("Retrieved %d ingest sources", len(entities))
        return entities

    def get_by_source_path(self, source_path: str) -> Optional[IngestSourceEntity]:
        """Get a single entity by exact source path."""
        logger.debug("Fetching ingest source by source_path='%s'", source_path)
        row = self._fetchone(
            "SELECT * FROM ingest_source WHERE source_path = ?", (source_path,)
        )
        if row is None:
            logger.debug("No ingest source found with source_path='%s'", source_path)
            return None
        entity = self._row_to_entity(dict(row))
        logger.debug("Found ingest source: %s", entity)
        return entity

    def get_by_title(self, title: str) -> List[IngestSourceEntity]:
        """Get entities by fuzzy title match."""
        logger.debug("Fetching ingest sources with title like '%%%s%%'", title)
        rows = self._fetchall(
            "SELECT * FROM ingest_source WHERE title LIKE ? ORDER BY id",
            (f"%{title}%",),
        )
        if rows is None:
            logger.debug("No ingest sources found matching title='%s'", title)
            return []
        entities = [self._row_to_entity(dict(row)) for row in rows]
        logger.debug("Retrieved %d ingest sources matching title='%s'", len(entities), title)
        return entities

    def delete_all(self) -> None:
        """删除所有导入源记录（需在事务中调用以保证一致性）。"""
        logger.debug("Deleting all ingest sources")
        try:
            with self._transaction() as conn:
                conn.execute("DELETE FROM ingest_source")
        except Exception as e:
            logger.error("Failed to delete all ingest sources: %s", e)
            raise
        logger.info("Deleted all ingest sources")

    #
    def _row_to_entity(self, row: Dict[str, Any]) -> IngestSourceEntity:
        """Convert a database row (after type conversion) to an entity."""
        data = self._from_db_row(row)
        return IngestSourceEntity.from_dict(data)

    @staticmethod
    def _to_db_row(data: Dict[str, Any]) -> Dict[str, Any]:
        """将实体字段转换为数据库行（包括 trigger_config 的组装）"""
        db_data = data.copy()

        # 处理 trigger_config：如果存在实体拆分字段，则组装成 JSON 字符串
        if "trigger_config" not in db_data:
            # 从拆分字段构建 trigger_config
            trigger_dict = {
                "update_mode": db_data.get("update_mode", "scheduled_time"),
                "device_trigger": {
                    "enabled": db_data.get("device_trigger_enabled", False)
                },
                "scheduled": {
                    "enabled": db_data.get("scheduled_enabled", False),
                    "time": db_data.get("scheduled_time") or None,
                    "interval": db_data.get("interval_time") or None,
                }
            }
            db_data["trigger_config"] = trigger_dict
        # else:
        #     # 如果已经提供了 trigger_config，则直接使用（可能是字典）
        #     trigger_dict = db_data["trigger_config"]

        # 移除拆分字段，避免它们直接写入数据库（数据库没有这些列）
        for field in ["update_mode", "device_trigger_enabled", "scheduled_enabled",
                      "scheduled_time", "interval_time"]:
            db_data.pop(field, None)

        # 将 target 字段映射为 target_path（如果调用方使用了 target）
        if "target" in db_data:
            db_data["target_path"] = db_data.pop("target")

        # 转换布尔字段
        for field in IngestSource.BOOL_FIELDS:
            if field in db_data and isinstance(db_data[field], bool):
                db_data[field] = int(db_data[field])

        # 转换 JSON 字段
        for field in IngestSource.JSON_FIELDS:
            if field in db_data and db_data[field] is not None:
                db_data[field] = json.dumps(db_data[field], ensure_ascii=False)

        # 只保留数据库允许的列
        db_data = {k: v for k, v in db_data.items() if k in IngestSource.ALLOWED_FIELDS}
        return db_data

    @staticmethod
    def _from_db_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """将数据库行转换为实体友好的字典（包括 trigger_config 的拆分）"""
        data = dict(row)

        # 转换布尔字段
        for field in IngestSource.BOOL_FIELDS:
            if field in data and data[field] is not None:
                data[field] = bool(data[field])

        # 转换 JSON 字段
        for field in IngestSource.JSON_FIELDS:
            if field in data and data[field] is not None:
                try:
                    data[field] = json.loads(data[field])
                except (json.JSONDecodeError, TypeError):
                    data[field] = None

        # 处理 trigger_config：拆分为实体字段
        trigger_config = data.pop("trigger_config", None)
        if isinstance(trigger_config, str):
            try:
                trigger_config = json.loads(trigger_config)
            except json.JSONDecodeError:
                trigger_config = None

        if isinstance(trigger_config, dict):
            data["update_mode"] = trigger_config.get("update_mode", "scheduled_time")
            device_trigger = trigger_config.get("device_trigger", {})
            data["device_trigger_enabled"] = device_trigger.get("enabled", False)
            scheduled = trigger_config.get("scheduled", {})
            data["scheduled_enabled"] = scheduled.get("enabled", False)
            data["scheduled_time"] = scheduled.get("time") or ""
            data["interval_time"] = scheduled.get("interval") or ""
        else:
            # 如果 trigger_config 缺失，提供默认值
            data.setdefault("update_mode", "scheduled_time")
            data.setdefault("device_trigger_enabled", False)
            data.setdefault("scheduled_enabled", False)
            data.setdefault("scheduled_time", "")
            data.setdefault("interval_time", "")

        # 将 target_path 映射回 target（可选，实体中使用 target_path 即可）
        # 这里直接保留 target_path，不需要映射，因为实体已改名为 target_path

        return data
