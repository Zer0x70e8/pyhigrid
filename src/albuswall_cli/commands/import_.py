# 
"""导入资产子命令"""
import json
import sys
import uuid
import hashlib
import mimetypes
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# 可选依赖：Pillow
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from albuswall.domain.entities import FileImportInfo
from albuswall.infrastructure.database import Connector
from albuswall.repositories.importer import ImportRepository
from albuswall.repositories.ingest_source import IngestSourceRepository
from ..utils.random_utils import generate_random_fileinfo

logger = logging.getLogger(__name__)


def create_fileinfo_from_path(
    file_path: str,
    source_id: int,
    relative_path: Optional[str] = None,
) -> FileImportInfo:
    """
    根据真实文件绝对路径创建 FileImportInfo，并关联 source_id。

    :param file_path: 用于读取元数据的绝对路径
    :param source_id: 导入源 ID
    :param relative_path: 最终存入数据库的相对路径（相对于 source_path）
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"file: {file_path}")

    original_name = path.name
    file_size = path.stat().st_size
    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type:
        mime_type = "application/octet-stream"

    # 计算 SHA-256
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()

    width = 0
    height = 0
    taken_at = None

    mtime = datetime.fromtimestamp(path.stat().st_mtime)

    if HAS_PIL and mime_type.startswith("image/"):
        try:
            with Image.open(path) as img:
                width, height = img.size
                exif = img.getexif()
                if exif:
                    taken_tag = 36867
                    if taken_tag in exif:
                        raw = exif[taken_tag]
                        taken_at = raw.replace(" ", "T").replace(":", "-", 2)
        except Exception as e:
            logger.warning("读取 EXIF 失败 (%s): %s", file_path, e)

    if not taken_at:
        taken_at = mtime.isoformat()

    # 决定存储的路径：优先使用相对路径，否则使用绝对路径
    stored_path = relative_path if relative_path is not None else str(path)

    return FileImportInfo(
        uuid=str(uuid.uuid4()),
        file_path=stored_path,
        original_name=original_name,
        mime_type=mime_type,
        file_hash=file_hash,
        file_size=file_size,
        width=width,
        height=height,
        taken_at=taken_at,
        thumb_path="",
        thumb_small_path="",
        thumb_medium_path="",
        source_id=source_id,
    )


def parse_fileinfo_from_dict(
    data: dict,
    source_id: int,
    relative_path: Optional[str] = None,
) -> FileImportInfo:
    """从字典构造 FileImportInfo，并关联 source_id，支持存储相对路径"""
    return FileImportInfo(
        uuid=data.get("uuid", str(uuid.uuid4())),
        file_path=relative_path if relative_path is not None else data.get("file_path", ""),
        original_name=data.get("original_name", "unknown"),
        mime_type=data.get("mime_type", "application/octet-stream"),
        file_hash=data.get("file_hash", ""),
        file_size=data.get("file_size", 0),
        width=data.get("width", 0),
        height=data.get("height", 0),
        taken_at=data.get("taken_at"),
        thumb_path=data.get("thumb_path", ""),
        thumb_small_path=data.get("thumb_small_path", ""),
        thumb_medium_path=data.get("thumb_medium_path", ""),
        source_id=source_id,
    )


def _to_absolute(rel_path: str, source_path: str) -> str:
    """将相对于 source_path 的相对路径转换为绝对路径，并检查是否为绝对路径"""
    p = Path(rel_path)
    if p.is_absolute():
        raise ValueError(f"路径必须是相对于源的相对路径，不能是绝对路径: {rel_path}")
    abs_path = (Path(source_path) / p).resolve()
    return str(abs_path)


# ---------------------------------------------------------------------------
# 子命令注册
# ---------------------------------------------------------------------------
def register(subparsers):
    import_parser = subparsers.add_parser("import", help="导入资产")
    import_parser.add_argument(
        "--source-id",
        type=int,
        required=True,
        help="导入源 ID（对应 ingest_source 表主键），必须存在"
    )
    import_parser.add_argument(
        "files", nargs="*", help="要导入的文件路径（相对于源路径）；与 --json 互斥"
    )
    import_parser.add_argument(
        "--json",
        help="JSON 元数据文件路径（包含文件信息）；与 files 互斥"
    )
    import_parser.add_argument(
        "--count", type=int, default=None,
        help="随机生成的资产数量（默认 5，仅在未提供 files 和 --json 时使用）"
    )
    import_parser.add_argument(
        "--albums", nargs="*", default=[],
        help="额外关联的相簿 UUID 列表"
    )
    import_parser.add_argument(
        "--json-output", action="store_true",
        help="以 JSON 格式输出导入结果"
    )
    import_parser.set_defaults(func=run)


# ---------------------------------------------------------------------------
# 命令执行
# ---------------------------------------------------------------------------
def run(args):
    connector = Connector(Path(args.db))
    import_repo = ImportRepository(connector)
    ingest_repo = IngestSourceRepository(connector)

    if args.json and args.files:
        print("错误：不能同时使用 --json 和文件路径参数。", file=sys.stderr)
        sys.exit(1)

    # 获取 source 信息
    source = ingest_repo.get_by_id(args.source_id)
    if source is None:
        print(f"错误：导入源 ID {args.source_id} 不存在。", file=sys.stderr)
        sys.exit(1)
    source_path = source["source_path"]

    file_infos: List[FileImportInfo] = []

    if args.json:
        with open(args.json, "r", encoding="utf-8") as f:
            raw = json.load(f)
        items = raw if isinstance(raw, list) else [raw]
        for item in items:
            try:
                rel = item.get("file_path", "")
                if not rel:
                    raise ValueError("JSON 条目缺少 file_path 字段")
                # 检查相对路径是否合法（不能是绝对路径）
                abs_path = _to_absolute(rel, source_path)
                # 存储相对路径
                file_infos.append(parse_fileinfo_from_dict(item, args.source_id, rel))
            except Exception as e:
                logger.error("跳过 JSON 条目 %s: %s", item, e)
    elif args.files:
        for fp in args.files:
            try:
                abs_path = _to_absolute(fp, source_path)
                # 计算相对路径（相对于 source_path）
                rel_path = str(Path(abs_path).relative_to(Path(source_path)))
                file_infos.append(
                    create_fileinfo_from_path(abs_path, args.source_id, rel_path)
                )
            except Exception as e:
                logger.error("跳过文件 %s: %s", fp, e)
    else:
        # 随机生成模式
        count = args.count if args.count is not None else 5
        for _ in range(count):
            info = generate_random_fileinfo()
            # 如果生成的对象支持设置 source_id，则设置；否则可能需要重新构造
            info.source_id = args.source_id
            file_infos.append(info)

    if not file_infos:
        print("没有可导入的数据。")
        return

    target_albums = args.albums or []

    # batch_import_files 不接受 source_id 参数，source_id 已包含在 FileImportInfo 中
    result = import_repo.batch_import_files(
        file_infos,
        target_album_uuids=target_albums
    )

    if args.json_output:
        print(json.dumps({
            "inserted": result.inserted,
            "skipped": result.skipped
        }, ensure_ascii=False, indent=2))
    else:
        print(f"Import complete: Success {result.inserted}, Skipped {result.skipped}")
