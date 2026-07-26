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
from typing import List

# 可选依赖：Pillow
try:
    # noinspection PyUnusedImports
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from albuswall.domain.entities import FileImportInfo
from albuswall.infrastructure.database import Connector
from albuswall.repository.importer import ImportRepository
from ..utils.random_utils import generate_random_fileinfo

logger = logging.getLogger(__name__)


def create_fileinfo_from_path(file_path: str) -> FileImportInfo:
    """根据真实文件路径创建 FileImportInfo，尽可能提取元数据"""
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

    # 默认值
    width = 0
    height = 0
    taken_at = None

    # 文件修改时间作为后备
    mtime = datetime.fromtimestamp(path.stat().st_mtime)

    if HAS_PIL and mime_type.startswith("image/"):
        try:
            with Image.open(path) as img:
                width, height = img.size
                exif = img.getexif()
                if exif:
                    # 36867 = DateTimeOriginal
                    taken_tag = 36867
                    if taken_tag in exif:
                        raw = exif[taken_tag]
                        # "YYYY:MM:DD HH:MM:SS" → ISO
                        taken_at = raw.replace(" ", "T").replace(":", "-", 2)
        except Exception as e:
            logger.warning("读取 EXIF 失败 (%s): %s", file_path, e)

    if not taken_at:
        taken_at = mtime.isoformat()

    asset_uuid = str(uuid.uuid4())

    return FileImportInfo(
        uuid=asset_uuid,
        file_path=str(path),
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
    )


def parse_fileinfo_from_dict(data: dict) -> FileImportInfo:
    """从字典（例如 JSON 导入）构造 FileImportInfo"""
    return FileImportInfo(
        uuid=data.get("uuid", str(uuid.uuid4())),
        file_path=data.get("file_path", ""),
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
    )


# ---------------------------------------------------------------------------
# 子命令注册
# ---------------------------------------------------------------------------
def register(subparsers):
    """注册 import 子命令到 argparse subparsers"""
    import_parser = subparsers.add_parser("import", help="导入资产")
    import_parser.add_argument(
        "files", nargs="*", help="要导入的文件路径（可多个）；与 --json 互斥"
    )
    import_parser.add_argument(
        "--json",
        help="JSON 元数据文件路径（包含文件信息）；与 files 互斥",
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
    """执行 import 命令"""
    connector = Connector(Path(args.db))
    repo = ImportRepository(connector)

    # 互斥性检查
    if args.json and args.files:
        print("错误：不能同时使用 --json 和文件路径参数。", file=sys.stderr)
        sys.exit(1)

    # 确定数据源
    file_infos: List[FileImportInfo] = []

    if args.json:
        with open(args.json, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list):
            for item in raw:
                file_infos.append(parse_fileinfo_from_dict(item))
        else:
            file_infos.append(parse_fileinfo_from_dict(raw))
    elif args.files:
        for fp in args.files:
            try:
                file_infos.append(create_fileinfo_from_path(fp))
            except Exception as e:
                logger.error("跳过文件 %s: %s", fp, e)
    else:
        count = args.count if args.count is not None else 5
        file_infos = [generate_random_fileinfo() for _ in range(count)]

    if not file_infos:
        print("没有可导入的数据。")
        return

    # 相簿关联（如果仓库支持）
    target_albums = args.albums or []
    if target_albums:
        try:
            result = repo.batch_import_files(file_infos, target_album_uuids=target_albums)
        except TypeError:
            logger.warning("当前仓库不支持 target_album_uuids，将忽略相簿关联。")
            result = repo.batch_import_files(file_infos)
    else:
        result = repo.batch_import_files(file_infos)

    # 输出结果
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Import complete: Success {result.inserted}, Skipped {result.skipped}")
