#
"""
ImportRepository — dedicated to background import services
"""

import dataclasses
from typing import List, Optional, Dict, Any, Union
from sqlite3 import IntegrityError

from albuswall.domain.enums import BaseAlbum
from albuswall.domain.entities import FileImportInfo
from .base import BaseRepository
from .utils.sql_helpers import placeholders, filter_dict


@dataclasses.dataclass
class BatchImportResult:
    """Batch import result"""
    inserted: int
    skipped: int


class ImportRepository(BaseRepository):
    # Fields allowed for INSERT (corresponding to the assets table, excluding auto-generated id, created_at, etc.)
    ASSET_INSERT_FIELDS = {
        "uuid", "file_path", "thumb_path", "thumb_small_path", "thumb_medium_path",
        "original_name", "mime_type", "file_hash", "file_size", "width", "height",
        "taken_at", "city", "exif_json", "is_favorite", "source_id",
    }

    # Virtual albums that must be associated by default during import
    DEFAULT_VIRTUAL_ALBUMS = [BaseAlbum.ALL_PHOTOS, BaseAlbum.UNORGANIZED]

    # ------------------------------------------------------------------
    # Public import methods
    # ------------------------------------------------------------------

    def import_file(self,
                    file_info: Union['FileImportInfo', Dict[str, Any]],
                    target_album_uuids: Optional[List[str]] = None) -> Optional[int]:
        """
        Import a single file, return the new asset_id; return None if the file is a duplicate.
        """
        data = self._to_dict(file_info)
        self._validate_required(data)

        with self._transaction() as conn:
            # 1. Proactive deduplication
            if conn.execute(
                "SELECT 1 FROM assets WHERE file_hash = ? AND is_deleted = 0",
                (data["file_hash"],)
            ).fetchone():
                self.logger.info("Skipping duplicate file: %s", data.get("original_name"))
                return None

            # 2. Resolve album IDs
            album_ids = self._resolve_album_ids_in_conn(conn, target_album_uuids or [])

            # 3. Perform import
            try:
                asset_id = self._import_asset_in_conn(conn, data, album_ids)
            except IntegrityError as e:
                if "file_hash" in str(e):
                    self.logger.info(
                        "Concurrent conflict, skipping duplicate file: %s",
                        data.get("original_name")
                    )
                    return None
                raise

            return asset_id

    def batch_import_files(self,
                           files: List[Union['FileImportInfo', Dict[str, Any]]],
                           target_album_uuids: Optional[List[str]] = None
                           ) -> BatchImportResult:
        """
        Batch import files in a single transaction.
        Duplicate files are skipped automatically; other database errors cause a full rollback.
        """
        uuids = target_album_uuids or []
        data_list = [self._to_dict(f) for f in files]
        for idx, data in enumerate(data_list, start=1):
            try:
                self._validate_required(data)
            except ValueError as e:
                raise ValueError(f"File {idx} is missing required fields: {e}") from e

        with self._transaction() as conn:
            # 1. Build set of input hashes and query existing hashes in one go
            input_hashes = {d["file_hash"] for d in data_list}
            existing_hashes = set()
            if input_hashes:
                query = (f"SELECT file_hash FROM assets WHERE file_hash "
                         f"IN ({placeholders(len(input_hashes))}) AND is_deleted = 0")
                rows = conn.execute(query, tuple(input_hashes)).fetchall()
                existing_hashes = {row["file_hash"] for row in rows}

            # 2. Filter out data based on existing hashes and handle duplicates within the list itself
            seen_hashes = set()
            filtered_data = []
            skipped = 0
            for d in data_list:
                h = d["file_hash"]
                if h in existing_hashes or h in seen_hashes:
                    skipped += 1
                    self.logger.debug("Skipping duplicate file: %s", d.get("original_name"))
                    continue
                seen_hashes.add(h)
                filtered_data.append(d)

            # 3. Resolve album IDs (default + extra)
            album_ids = self._resolve_album_ids_in_conn(conn, uuids)

            # 4. Insert and associate each item
            inserted = 0
            for data in filtered_data:
                try:
                    self._import_asset_in_conn(conn, data, album_ids)
                    inserted += 1
                except IntegrityError as e:
                    if "file_hash" in str(e):
                        skipped += 1
                        self.logger.debug(
                            "Concurrent conflict, skipping file: %s",
                            data.get("original_name")
                        )
                        continue
                    raise  # Other constraint errors cause transaction rollback

            return BatchImportResult(inserted=inserted, skipped=skipped)

    # ------------------------------------------------------------------
    # Internal atomic operations
    # ------------------------------------------------------------------

    def _import_asset_in_conn(
            self,
            conn,
            data: Dict[str, Any],
            album_ids: List[int]
    ) -> int:
        """
        Perform asset insertion and album association on the given connection, return asset_id.
        Does not handle duplicate conflicts; the caller is responsible for catching IntegrityError.
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
                pass  # Ignore if association already exists
        return asset_id

    def _insert_asset_in_conn(self, conn, data: Dict[str, Any]) -> int:
        """Insert asset row and return lastrowid."""
        allowed = filter_dict(data, self.ASSET_INSERT_FIELDS)
        # Set default value for is_favorite
        allowed.setdefault("is_favorite", 0)

        columns = list(allowed.keys())
        values = list(allowed.values())
        sql = f"INSERT INTO assets ({', '.join(columns)}) VALUES ({placeholders(len(columns))})"
        cursor = conn.execute(sql, values)
        return cursor.lastrowid

    # ------------------------------------------------------------------
    # Album ID resolution
    # ------------------------------------------------------------------

    def _resolve_album_ids_in_conn(self, conn, extra_uuids: List[str]) -> List[int]:
        """
        Return a list of all album ids that need to be associated:
        - Default virtual albums: ensure they exist and return their ids
        - Extra specified albums: only query; silently ignore if not found
        """
        album_ids = []

        # 1. Default virtual albums (batch query, create if needed)
        default_uuids = [str(alb.uuid) for alb in self.DEFAULT_VIRTUAL_ALBUMS]
        # Query existing and not deleted
        rows = conn.execute(
            f"SELECT uuid, id FROM albums WHERE uuid IN ("
            f"{placeholders(len(default_uuids))}"
            f") AND is_deleted = 0",
            default_uuids
        ).fetchall()
        existing_map = {row["uuid"]: row["id"] for row in rows}

        for alb in self.DEFAULT_VIRTUAL_ALBUMS:
            uid = str(alb.uuid)
            if uid in existing_map:
                album_ids.append(existing_map[uid])
            else:
                # Not exists or soft deleted -> create/restore
                conn.execute(
                    """INSERT INTO albums (uuid, title, album_type, is_deleted)
                       VALUES (?, ?, ?, 0)
                       ON CONFLICT(uuid) DO UPDATE SET is_deleted = 0""",
                    (uid, alb.label, alb.album_type.value)
                )
                # Re-fetch id
                new_id = conn.execute(
                    "SELECT id FROM albums WHERE uuid = ?", (uid,)
                ).fetchone()["id"]
                album_ids.append(new_id)

        # 2. Extra albums (query only)
        if extra_uuids:
            rows = conn.execute(
                f"SELECT id FROM albums WHERE uuid IN ("
                f"{placeholders(len(extra_uuids))}"
                f") AND is_deleted = 0",
                extra_uuids
            ).fetchall()
            album_ids.extend(row["id"] for row in rows)

        return album_ids

    # Utility methods
    @staticmethod
    def _to_dict(file_info) -> Dict[str, Any]:
        """Convert to dict uniformly."""
        if isinstance(file_info, FileImportInfo):
            return dataclasses.asdict(file_info)
        if isinstance(file_info, dict):
            return file_info
        raise TypeError("file_info must be a FileImportInfo instance or a dict")

    @classmethod
    def _validate_required(cls, data: Dict[str, Any]):
        """Validate required fields for import."""
        required_fields = ["uuid", "file_path", "file_hash", "original_name", "mime_type"]
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Import data missing required field: {field}")
