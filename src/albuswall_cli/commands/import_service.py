#
"""
import-service 子命令：用于测试后台导入服务及自动导入功能。
"""

import logging
import sys
import time
from pathlib import Path

from albuswall.infrastructure.database import Connector
from albuswall.repositories.importer import ImportRepository, FileImportInfo
from albuswall.repositories.ingest_source import IngestSourceRepository
from albuswall.services.import_ import ImportService

logger = logging.getLogger(__name__)


def register(subparsers):
    parser = subparsers.add_parser(
        "import-service",
        help="管理后台导入服务（自动导入、暂停、恢复等）"
    )
    sub = parser.add_subparsers(dest="action", required=True)

    # start
    p_start = sub.add_parser("start", help="启动自动导入任务")
    p_start.add_argument("source_id", type=int, help="ingest_source 的 ID")
    p_start.set_defaults(func=cmd_start)

    # pause
    p_pause = sub.add_parser("pause", help="暂停自动导入任务")
    p_pause.add_argument("source_id", type=int)
    p_pause.set_defaults(func=cmd_pause)

    # resume
    p_resume = sub.add_parser("resume", help="恢复自动导入任务")
    p_resume.add_argument("source_id", type=int)
    p_resume.set_defaults(func=cmd_resume)

    # stop
    p_stop = sub.add_parser("stop", help="停止自动导入任务")
    p_stop.add_argument("source_id", type=int)
    p_stop.set_defaults(func=cmd_stop)

    # status
    p_status = sub.add_parser("status", help="查看导入任务进度")
    p_status.add_argument("source_id", type=int)
    p_status.set_defaults(func=cmd_status)

    # update
    p_update = sub.add_parser("update", help="更新 ingest_source 配置")
    p_update.add_argument("source_id", type=int)
    p_update.add_argument("--target-path", dest="target_path", help="新的目标路径")
    p_update.add_argument("--source-path", dest="source_path", help="新的源路径")
    p_update.add_argument("--auto-mount", dest="auto_mount", type=bool, help="是否自动挂载")
    p_update.set_defaults(func=cmd_update)

    # submit
    p_submit = sub.add_parser("submit", help="手动提交文件列表进行导入测试")
    p_submit.add_argument("source_id", type=int, help="ingest_source ID，用于设置文件的 source_id")
    p_submit.add_argument("files", nargs="+", help="文件绝对路径列表")
    p_submit.add_argument("--album", dest="album_uuids", action="append", help="额外关联相簿 UUID，可多次指定")
    p_submit.set_defaults(func=cmd_submit)

    parser.set_defaults(func=dispatch)


def dispatch(args):
    args.func(args)


def _create_service(db_path: Path) -> ImportService:
    """创建导入服务实例并启动后台线程"""
    connector = Connector(db_path)
    import_repo = ImportRepository(connector)
    ingest_repo = IngestSourceRepository(connector)
    service = ImportService(import_repo, ingest_repo)
    service.start()
    return service


def cmd_start(args):
    db_path = Path(args.db)
    service = _create_service(db_path)
    try:
        task = service.start_auto_import(args.source_id)
        print(f"自动导入任务已启动 (source_id={args.source_id})")
        while True:
            progress = task.get_progress()
            status = progress["status"]
            print(
                f"\r状态: {status} | 已处理: {progress['processed_files']}/{progress['total_files']} "
                f"| 导入: {progress['imported_files']} | 跳过: {progress['skipped_files']}",
                end=""
            )
            if status in ("finished", "error", "stopped"):
                print()
                if status == "error":
                    print(f"错误: {progress['error']}", file=sys.stderr)
                    sys.exit(1)
                break
            time.sleep(0.5)
    except Exception as e:
        print(f"启动失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_pause(args):
    service = _create_service(Path(args.db))
    try:
        service.pause_auto_import(args.source_id)
        print(f"已发送暂停命令 (source_id={args.source_id})")
    except Exception as e:
        print(f"暂停失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_resume(args):
    service = _create_service(Path(args.db))
    try:
        service.resume_auto_import(args.source_id)
        print(f"已发送恢复命令 (source_id={args.source_id})")
    except Exception as e:
        print(f"恢复失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_stop(args):
    service = _create_service(Path(args.db))
    try:
        service.stop_auto_import(args.source_id)
        print(f"已发送停止命令 (source_id={args.source_id})")
    except Exception as e:
        print(f"停止失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args):
    service = _create_service(Path(args.db))
    try:
        progress = service.get_auto_import_progress(args.source_id)
        if progress:
            print(f"Source ID: {progress['source_id']}")
            print(f"Status: {progress['status']}")
            print(f"Total files: {progress['total_files']}")
            print(f"Processed: {progress['processed_files']}")
            print(f"Imported: {progress['imported_files']}")
            print(f"Skipped: {progress['skipped_files']}")
            if progress['error']:
                print(f"Error: {progress['error']}")
        else:
            print(f"没有找到 source_id={args.source_id} 的任务")
    except Exception as e:
        print(f"查询失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_update(args):
    connector = Connector(Path(args.db))
    ingest_repo = IngestSourceRepository(connector)
    updates = {}
    if args.target_path is not None:
        updates["target_path"] = args.target_path
    if args.source_path is not None:
        updates["source_path"] = args.source_path
    if args.auto_mount is not None:
        updates["auto_mount"] = args.auto_mount
    if not updates:
        print("没有提供要更新的字段", file=sys.stderr)
        sys.exit(1)
    try:
        success = ingest_repo.update(args.source_id, **updates)
        if success:
            print(f"更新成功 (source_id={args.source_id})")
        else:
            print("更新失败，可能记录不存在")
            sys.exit(1)
    except Exception as e:
        print(f"更新失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_submit(args):
    service = _create_service(Path(args.db))
    files = []
    import uuid, hashlib, os
    for fpath in args.files:
        p = Path(fpath)
        if not p.exists():
            print(f"文件不存在: {fpath}", file=sys.stderr)
            continue
        with open(fpath, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        info = FileImportInfo(
            uuid=str(uuid.uuid4()),
            file_path=fpath,
            original_name=p.name,
            mime_type="application/octet-stream",
            file_hash=file_hash,
            file_size=os.path.getsize(fpath),
            width=None,
            height=None,
            taken_at=None,
            city=None,
            exif_json=None,
            is_favorite=False,
            source_id=args.source_id,
        )
        files.append(info)

    if not files:
        print("没有有效的文件可导入", file=sys.stderr)
        sys.exit(1)

    task = service.submit_import(files, args.album_uuids)
    print("手动导入任务已提交，等待完成...")
    task.wait()
    if task.error:
        print(f"导入失败: {task.error}", file=sys.stderr)
        sys.exit(1)
    else:
        result = task.result
        print(f"导入完成: 插入 {result.inserted} 个，跳过 {result.skipped} 个")
