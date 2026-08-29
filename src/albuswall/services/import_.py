#
"""
Background import service module, containing automatic import tasks and manual import queue service.
"""

import os
import queue
import threading
import logging
import uuid
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable, Union

from albuswall.repositories.importer import (
    ImportRepository,
    FileImportInfo,
    BatchImportResult,
)
from albuswall.repositories.ingest_source import IngestSourceRepository
from albuswall.core.build_logger import TRACE

from .common import LOGGER_HEAD

logger = logging.getLogger(f"{LOGGER_HEAD}.importer")


class ImportTask:
    """Encapsulates a manual batch import task, providing a synchronous waiting interface."""

    def __init__(self, files: List[Union[FileImportInfo, Dict[str, Any]]],
                 album_uuids: Optional[List[str]] = None):
        self.files = files
        self.album_uuids = album_uuids
        self.result: Optional[BatchImportResult] = None
        self.error: Optional[Exception] = None
        self._done_event = threading.Event()
        logger.log(TRACE, "ImportTask created with %d file(s)", len(files))

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._done_event.wait(timeout)

    def done(self) -> bool:
        return self._done_event.is_set()

    def _set_done(self, result=None, error=None):
        self.result = result
        self.error = error
        self._done_event.set()
        logger.log(TRACE, "ImportTask completed: result=%s error=%s", result, error)


class AutoImportTask:
    """Responsible for scanning one ingest_source and executing import, supporting pause/resume/stop."""

    BATCH_SIZE = 100  # number of files processed per batch

    def __init__(self, source_id: int,
                 import_repo: ImportRepository,
                 ingest_repo: IngestSourceRepository):
        self.source_id = source_id
        self._import_repo = import_repo
        self._ingest_repo = ingest_repo
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Progress information
        self.total_files = 0
        self.processed_files = 0
        self.imported_files = 0
        self.skipped_files = 0
        self.status = "idle"
        self.error: Optional[Exception] = None

        # Callback function used to notify progress updates
        self.progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    # ---------- Control methods ----------
    def start(self):
        if self._thread and self._thread.is_alive():
            logger.debug("Auto import task for source_id=%d is already running", self.source_id)
            return
        self._stop_event.clear()
        self._pause_event.set()
        self.status = "scanning"
        self._thread = threading.Thread(
            target=self._run, name=f"AutoImport-{self.source_id}", daemon=True
        )
        self._thread.start()
        logger.info("Auto import task started for source_id=%d", self.source_id)

    def pause(self):
        self._pause_event.clear()
        if self.status not in ("finished", "error", "stopped"):
            self.status = "paused"
            self._notify_progress()
        logger.info("Auto import task paused for source_id=%d", self.source_id)

    def resume(self):
        self._pause_event.set()
        if self.status == "paused":
            self.status = "scanning"
            self._notify_progress()
        logger.info("Auto import task resumed for source_id=%d", self.source_id)

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()  # wake up possible pause waiting
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Auto import task stop requested for source_id=%d", self.source_id)

    # ---------- Internal execution ----------
    def _run(self):
        logger.log(TRACE, "Auto import _run started for source_id=%d", self.source_id)
        try:
            # First fetch source configuration
            source = self._ingest_repo.get_by_id(self.source_id)
            if not source:
                raise ValueError(f"ingest_source {self.source_id} does not exist")

            logger.debug("Fetched ingest source config for source_id=%d: %s", self.source_id, source)

            # Use streaming scan, processing files as they are discovered
            file_iterator = self._scan_files(source)
            batch = []
            self.total_files = 0  # dynamic update, may not be accurate

            for abs_path in file_iterator:
                if self._stop_event.is_set():
                    self.status = "stopped"
                    self._notify_progress()
                    logger.info("Auto import task stopped for source_id=%d", self.source_id)
                    return
                self._wait_if_paused()

                batch.append(abs_path)
                if len(batch) >= self.BATCH_SIZE:
                    self._process_batch(batch, source)
                    batch = []

            # Process remaining files that are fewer than one batch
            if batch:
                self._process_batch(batch, source)

            self.status = "finished"
            self._notify_progress()
            logger.info("Auto import task finished for source_id=%d", self.source_id)
        except Exception as e:
            logger.exception("Auto import task failed for source_id=%d", self.source_id)
            self.status = "error"
            self.error = e
            self._notify_progress()

    def _process_batch(self, file_paths: List[str], source: Dict[str, Any]):
        """Process a batch of files: extract metadata and import."""
        logger.log(TRACE, "Processing batch of %d files for source_id=%d", len(file_paths), self.source_id)
        infos = []
        source_path = source["source_path"]
        for abs_path in file_paths:
            # Convert to relative path
            rel_path = os.path.relpath(abs_path, source_path)
            info = self._extract_metadata(abs_path, rel_path, source["id"])
            infos.append(info)

        logger.debug("Batch metadata extracted for %d files, importing...", len(infos))
        result = self._import_repo.batch_import_files(infos)
        self.processed_files += len(infos)
        self.imported_files += result.inserted
        self.skipped_files += result.skipped
        logger.info("Batch import completed for source_id=%d: inserted=%d skipped=%d",
                    self.source_id, result.inserted, result.skipped)
        self._notify_progress()

    def _wait_if_paused(self):
        while not self._pause_event.is_set() and not self._stop_event.is_set():
            self.status = "paused"
            self._notify_progress()
            logger.log(TRACE, "Auto import paused, waiting for resume or stop for source_id=%d", self.source_id)
            self._pause_event.wait(timeout=0.5)

    def _scan_files(self, source: Dict[str, Any]):
        """Stream scan the source directory, yielding absolute paths.

        Re-reads the source configuration each time to support dynamic updates.
        """
        source_path = source["source_path"]
        recursive = source.get("subfolder_recursion", False)
        file_type_check = source.get("file_type_check", False)
        file_types_raw = source.get("file_types") or []

        # Support string or list
        if isinstance(file_types_raw, str):
            file_types = [t.strip() for t in file_types_raw.split(",")]
        else:
            file_types = [str(t).lower() for t in file_types_raw]

        logger.log(TRACE, "Scanning source_id=%d: path=%s recursive=%s file_type_check=%s file_types=%s",
                   self.source_id, source_path, recursive, file_type_check, file_types)

        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")

        # Choose traversal method based on recursion flag
        iterator = path.rglob("*") if recursive else path.glob("*")

        for entry in iterator:
            if self._stop_event.is_set():
                logger.log(TRACE, "Stop event set during scan for source_id=%d", self.source_id)
                return
            self._wait_if_paused()
            if entry.is_file():
                if file_type_check and file_types:
                    if entry.suffix.lower() in file_types:
                        logger.log(TRACE, "Found file: %s", entry)
                        yield str(entry)
                else:
                    logger.log(TRACE, "Found file: %s", entry)
                    yield str(entry)

    def _extract_metadata(self, abs_path: str, rel_path: str, source_id: int) -> FileImportInfo:
        """Extract metadata from file to generate FileImportInfo.

        A more professional tool may be used in actual projects; this provides a basic implementation.
        """
        logger.log(TRACE, "Extracting metadata for %s", abs_path)
        # Calculate file hash
        with open(abs_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        # File size
        file_size = os.path.getsize(abs_path)

        # MIME type
        mime_type, _ = mimetypes.guess_type(abs_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        # Image dimensions (optional, if file is an image)
        width = height = None
        try:
            from PIL import Image
            with Image.open(abs_path) as img:
                width, height = img.size
        except Exception:
            pass

        # Capture time, EXIF etc. can be parsed as needed, left empty here
        taken_at = None
        exif_json = None

        logger.log(TRACE, "Metadata extracted for %s: mime=%s size=%d", abs_path, mime_type, file_size)

        return FileImportInfo(
            uuid=str(uuid.uuid4()),
            file_path=rel_path,          # relative path
            original_name=os.path.basename(abs_path),
            mime_type=mime_type,
            file_hash=file_hash,
            file_size=file_size,
            width=width,  # noqa
            height=height,  # noqa
            taken_at=taken_at,
            city=None,
            exif_json=exif_json,
            is_favorite=False,
            source_id=source_id,
        )

    def _notify_progress(self):
        logger.log(TRACE, "Notifying progress for source_id=%d: %s", self.source_id, self.get_progress())
        if self.progress_callback:
            self.progress_callback(self.get_progress())

    def get_progress(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "imported_files": self.imported_files,
            "skipped_files": self.skipped_files,
            "error": str(self.error) if self.error else None,
        }


class ImportService:
    """Background import service, managing manual task queue and automatic import tasks."""

    def __init__(self, import_repo: ImportRepository, ingest_repo: IngestSourceRepository):
        self._import_repo = import_repo
        self._ingest_source_repo = ingest_repo
        self._task_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        # Automatic task management
        self._auto_tasks: Dict[int, AutoImportTask] = {}
        self._auto_tasks_lock = threading.Lock()
        logger.log(TRACE, "ImportService initialized")

    # ---------- Lifecycle ----------
    def start(self):
        """Start background worker thread (for processing manually submitted tasks)."""
        if self._worker_thread and self._worker_thread.is_alive():
            logger.warning("Import service is already running")
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._worker_loop, name="ImportWorker", daemon=True
        )
        self._worker_thread.start()
        logger.info("Import service worker thread started")

    def stop(self, timeout: Optional[float] = None):
        """Stop background thread."""
        if not self._worker_thread or not self._worker_thread.is_alive():
            return
        self._stop_event.set()
        self._task_queue.put(None)  # sentinel
        self._worker_thread.join(timeout=timeout)
        if self._worker_thread.is_alive():
            logger.warning("Import service thread did not stop within %.1f seconds", timeout or -1)
        else:
            logger.info("Import service stopped")

    # ---------- Manual task submission ----------
    def submit_import(self, files, album_uuids=None) -> ImportTask:
        task = ImportTask(files, album_uuids)
        self._task_queue.put(task)
        logger.debug("Manual import task submitted with %d file(s)", len(files))
        return task

    # ---------- Automatic task management ----------
    def start_auto_import(self, source_id: int) -> AutoImportTask:
        with self._auto_tasks_lock:
            # If a task for the same source exists and is not finished, raise exception
            existing = self._auto_tasks.get(source_id)
            if existing and existing.status not in ("finished", "error", "stopped"):
                raise RuntimeError(f"Import task for source {source_id} is already running")
            # Create new task
            task = AutoImportTask(source_id, self._import_repo, self._ingest_source_repo)
            self._auto_tasks[source_id] = task
            # Set callback to auto cleanup after task ends
            task.progress_callback = lambda progress: self._on_task_progress(source_id, progress)
            task.start()
            logger.info("Auto import started for source_id=%d", source_id)
            return task

    def pause_auto_import(self, source_id: int):
        task = self._auto_tasks.get(source_id)
        if task:
            task.pause()
            logger.info("Auto import pause requested for source_id=%d", source_id)

    def resume_auto_import(self, source_id: int):
        task = self._auto_tasks.get(source_id)
        if task:
            task.resume()
            logger.info("Auto import resume requested for source_id=%d", source_id)

    def stop_auto_import(self, source_id: int):
        task = self._auto_tasks.get(source_id)
        if task:
            task.stop()
            logger.info("Auto import stop requested for source_id=%d", source_id)

    def get_auto_import_progress(self, source_id: int) -> Optional[Dict[str, Any]]:
        task = self._auto_tasks.get(source_id)
        return task.get_progress() if task else None

    def update_ingest_source(self, source_id: int, **kwargs):
        """Update source configuration; tasks re-read before next batch."""
        self._ingest_source_repo.update(source_id, **kwargs)
        logger.debug("Ingest source updated for source_id=%d with %s", source_id, kwargs)

    def _on_task_progress(self, source_id: int, progress: Dict[str, Any]):
        """Task progress callback: auto cleanup when task ends."""
        if progress["status"] in ("finished", "error", "stopped"):
            with self._auto_tasks_lock:
                task = self._auto_tasks.get(source_id)
                if task and task.status in ("finished", "error", "stopped"):
                    del self._auto_tasks[source_id]
                    logger.debug("Cleaned up auto import task source_id=%d", source_id)

    # ---------- Worker thread loop ----------
    def _worker_loop(self):
        logger.log(TRACE, "Import worker loop started")
        while not self._stop_event.is_set():
            try:
                task = self._task_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if task is None:
                logger.log(TRACE, "Worker loop received sentinel, exiting")
                break
            logger.debug("Worker picked up a task")
            self._execute_task(task)
            self._task_queue.task_done()

    def _execute_task(self, task: ImportTask):
        logger.debug("Executing import task with %d file(s)", len(task.files))
        try:
            result = self._import_repo.batch_import_files(task.files, task.album_uuids)
            task._set_done(result=result)
            logger.info("Import task completed successfully: inserted=%d skipped=%d",
                        result.inserted, result.skipped)
        except Exception as e:
            logger.exception("Batch import execution failed")
            task._set_done(error=e)
