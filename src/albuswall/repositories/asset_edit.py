#
"""
资产编辑仓库 (AssetEditRepository)
"""

from typing import Dict, Any, Optional
from .base import BaseRepository
from .utils.sql_helpers import filter_dict, build_set_clause


class AssetEditRepository(BaseRepository):
    EDITABLE_FIELDS = {
        "original_name", "mime_type", "file_size", "width", "height",
        "taken_at", "city", "exif_json", "is_favorite", "thumb_path",
        "thumb_small_path", "thumb_medium_path",
        # 新增：允许编辑资产的导入源关联
        "source_id"
    }

    def update(self, asset_uuid: str, **fields) -> bool:
        updates = filter_dict(fields, self.EDITABLE_FIELDS)
        if not updates:
            return False

        if "is_favorite" in updates:
            updates["is_favorite"] = 1 if updates["is_favorite"] else 0

        set_clause, values = build_set_clause(updates)
        values.append(asset_uuid)

        cursor = self._execute(
            f"UPDATE assets SET {set_clause} WHERE uuid = ? AND is_deleted = 0",
            values
        )
        return cursor.rowcount > 0

    def debugger_asset_info_get(self, asset_uuid: str) -> Optional[Dict[str, Any]]:
        row = self._fetchone("SELECT * FROM assets WHERE uuid = ?", (asset_uuid,))
        if row is None:
            return None
        return dict(row)
