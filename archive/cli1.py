#!/usr/bin/env python3
"""
照片管理 CLI
基于 ImportRepository、ViewRepository、ViewAssetRepository 的命令行工具。
"""

import os
import sys
import json
import argparse
import hashlib
import uuid
import mimetypes
from pathlib import Path
from typing import Dict, Any


# 可选依赖：Pillow 用于读取图片尺寸和 EXIF 日期
try:
    from PIL import Image
    from PIL.ExifTags import Base as ExifBase
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
src_path = Path(__file__).parent.parent  # 指向 .../src
sys.path.insert(0, str(src_path))
print("cwd:", os.getcwd())

# from albuswall.domain.entities import FileImportInfo
from albuswall.domain.enums import BaseAlbum, AlbumAssetSortOption
from albuswall.infrastructure.database import Connector
from albuswall.repository.importer import ImportRepository
# from albuswall.repository.view import ViewRepository
from albuswall.repository.view_asset import ViewAssetRepository





def generate_file_info(file_path: str) -> Dict[str, Any]:
    """
    根据给定的文件路径生成导入所需的完整元数据字典。
    会自动计算文件哈希、MIME 类型、文件大小，并尝试读取图片尺寸和拍摄日期（需 Pillow）。
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    stat = os.stat(file_path)
    file_size = stat.st_size

    # MIME 类型
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"

    original_name = os.path.basename(file_path)

    # 计算 SHA-256 哈希
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    file_hash = sha.hexdigest()

    # 构造基础字典（对应 FileImportInfo 字段）
    info: Dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        "file_path": os.path.abspath(file_path),
        "thumb_path": None,          # 缩略图通常由其他服务生成，此处留空
        "thumb_small_path": None,
        "thumb_medium_path": None,
        "original_name": original_name,
        "mime_type": mime_type,
        "file_hash": file_hash,
        "file_size": file_size,
        "width": None,
        "height": None,
        "taken_at": None,
        "city": None,
        "exif_json": None,
        "is_favorite": 0,
    }

    # 如果是图片且 Pillow 可用，尝试读取尺寸和 EXIF 拍摄日期
    if HAS_PIL and mime_type.startswith("image/"):
        try:
            with Image.open(file_path) as img:
                info["width"], info["height"] = img.size
                exif_data = img.getexif()
                if exif_data:
                    # 36867 对应 DateTimeOriginal
                    taken_tag = 36867
                    if taken_tag in exif_data:
                        # EXIF 日期格式通常为 "YYYY:MM:DD HH:MM:SS"
                        taken_at = exif_data[taken_tag]
                        # 转换为 ISO 格式
                        info["taken_at"] = taken_at.replace(" ", "T").replace(":", "-", 2)
        except Exception as e:
            print(f"警告：无法读取 {file_path} 的 EXIF 信息: {e}", file=sys.stderr)

    return info


# ----------------------------------------------------------------------
# 数据库连接工厂
# ----------------------------------------------------------------------

def get_connector(db_path: str) -> Connector:
    """创建数据库连接器，确保传入 Path 对象（根据 connector.py 要求）"""
    return Connector(Path(db_path))


# ----------------------------------------------------------------------
# 子命令处理函数
# ----------------------------------------------------------------------

def cmd_import(args, connector: Connector):
    """执行导入操作"""
    repo = ImportRepository(connector)
    target_albums = args.albums or []

    # 根据参数来源决定数据来源
    if args.json:
        with open(args.json, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        # 统一转为列表处理
        if isinstance(raw_data, list):
            files_data = raw_data
        else:
            files_data = [raw_data]
    elif args.image:
        # 直接指定图片文件路径，为每个文件生成元数据
        files_data = []
        for path in args.image:
            try:
                info = generate_file_info(path)
                files_data.append(info)
            except Exception as e:
                print(f"跳过文件 {path}: {e}", file=sys.stderr)
        if not files_data:
            print("没有有效的文件可导入。", file=sys.stderr)
            return
    else:
        print("必须指定 --json 或 --image 参数。", file=sys.stderr)
        return

    # 调用批量导入（单个文件也走批量，接口统一）
    result = repo.batch_import_files(files_data, target_album_uuids=target_albums)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_list(args, connector: Connector):
    """列出所有照片视图中的资产"""
    repo = ViewAssetRepository(connector)

    # 解析排序枚举
    sort_map = {
        "taken_at": AlbumAssetSortOption.TAKEN_AT,
        "added_at": AlbumAssetSortOption.ADDED_AT,
        "sort_order": AlbumAssetSortOption.SORT_ORDER,
    }
    sort_by = sort_map.get(args.sort_by, AlbumAssetSortOption.TAKEN_AT)
    order = args.order.upper()
    limit = args.limit
    offset = (args.page - 1) * limit

    assets = repo.get_assets(
        view_id=BaseAlbum.ALL_PHOTOS,
        sort_by=sort_by,
        # order=order,
        offset=offset,
        limit=limit
    )

    # 将资产对象转为字典列表输出
    output = []
    for asset in assets:
        if hasattr(asset, "__dataclass_fields__"):
            # 如果是 dataclass，安全转换
            item = {k: str(v) if not isinstance(v, (int, float, bool, type(None))) else v
                    for k, v in asset.__dict__.items()}
        else:
            item = dict(asset)
        output.append(item)
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))


# ----------------------------------------------------------------------
# 主入口
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="照片管理命令行工具 - 导入与查询",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db", required=True, help="SQLite 数据库文件路径")

    subparsers = parser.add_subparsers(dest="command", required=True, help="可用命令")

    # ------ import 子命令 ------
    import_parser = subparsers.add_parser("import", help="导入文件（支持 JSON 元数据或直接图片文件）")
    import_group = import_parser.add_mutually_exclusive_group(required=True)
    import_group.add_argument(
        "--json",
        help="包含文件信息的 JSON 文件路径（单条对象或数组）",
    )
    import_group.add_argument(
        "--image",
        nargs="+",
        help="直接指定一个或多个图片文件路径，自动提取元数据",
    )
    import_parser.add_argument(
        "--albums",
        nargs="*",
        default=[],
        help="额外关联的相簿 UUID 列表（空格分隔）",
    )

    # ------ list 子命令 ------
    list_parser = subparsers.add_parser("list", help="列出“所有照片”视图中的资产")
    list_parser.add_argument(
        "--sort-by",
        choices=["taken_at", "added_at", "sort_order"],
        default="taken_at",
        help="排序字段 (默认: taken_at)",
    )
    list_parser.add_argument(
        "--order",
        choices=["asc", "desc"],
        default="desc",
        help="排序方向 (默认: desc)",
    )
    list_parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="页码 (从 1 开始，默认 1)",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="每页数量 (默认: 50)",
    )

    args = parser.parse_args()

    # 初始化数据库连接
    try:
        connector = get_connector(args.db)
    except Exception as e:
        print(f"无法连接到数据库 {args.db}: {e}", file=sys.stderr)
        sys.exit(1)

    # 执行对应命令
    if args.command == "import":
        cmd_import(args, connector)
    elif args.command == "list":
        cmd_list(args, connector)


if __name__ == "__main__":
    main()
