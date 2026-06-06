#!/usr/bin/env python3
"""
增强版照片管理 CLI — 融合测试与生产需求
支持：数据库初始化、导入（随机/文件/JSON）、视图查看（含分页与排序方向）
"""

import sys
import json
import uuid
import hashlib
import mimetypes
import random
import string
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 可选依赖：Pillow
try:
    # noinspection PyUnusedImports
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# 添加项目 src 路径，保证导入 pyhigrid
src_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(src_path))

from pyhigrid.domain.entities import FileImportInfo
from pyhigrid.domain.enums import AlbumAssetSortOption
from pyhigrid.infrastructure.database import Connector
from pyhigrid.repository.importer import ImportRepository
from pyhigrid.repository.view import ViewRepository
from pyhigrid.repository.view_asset import ViewAssetRepository
from pyhigrid.repository.asset_edit import AssetEditRepository

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("enhanced_cli")


# ============================================================================
# 辅助函数
# ============================================================================
def generate_random_fileinfo() -> FileImportInfo:
    """生成随机 FileImportInfo 用于测试导入"""
    uid = str(uuid.uuid4())
    name = "".join(random.choices(string.ascii_lowercase, k=8)) + ".jpg"
    path = f"/mock/import/{name}"
    mime = "image/jpeg"
    file_hash = "".join(random.choices("0123456789abcdef", k=64))
    size = random.randint(1000, 5000000)
    w, h = random.randint(800, 4000), random.randint(600, 3000)
    taken = (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat()
    return FileImportInfo(
        uuid=uid,
        file_path=path,
        original_name=name,
        mime_type=mime,
        file_hash=file_hash,
        file_size=size,
        width=w,
        height=h,
        taken_at=taken,
        thumb_path=f"/thumb/{name}",
        thumb_small_path=f"/thumb_small/{name}",
        thumb_medium_path=f"/thumb_medium/{name}",
    )


def create_fileinfo_from_path(file_path: str) -> FileImportInfo:
    """根据真实文件路径创建 FileImportInfo，尽可能提取元数据"""
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"文件不存在: {file_path}")

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


def parse_fileinfo_from_dict(data: Dict[str, Any]) -> FileImportInfo:
    """从字典（例如 JSON 导入）构造 FileImportInfo"""
    # 必要的字段缺失时给默认值，避免崩溃
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


# ============================================================================
# 数据库连接器工厂
# ============================================================================
def get_connector(db_path: str) -> Connector:
    return Connector(Path(db_path))


# ============================================================================
# 子命令：init
# ============================================================================
def cmd_init(args):
    db_path = Path(args.db)
    logger.info("正在初始化数据库: %s", db_path)
    connector = get_connector(str(db_path))
    try:
        conn = connector.connect()  # 自动建表/索引
        conn.close()
        print("数据库初始化成功。")
    except Exception as e:
        logger.error("初始化失败: %s", e)
        sys.exit(1)


# ============================================================================
# 子命令：import
# ============================================================================
def cmd_import(args):
    connector = get_connector(args.db)
    repo = ImportRepository(connector)

    # ----- 互斥性检查 -----
    if args.json and args.files:
        print("错误：不能同时使用 --json 和文件路径参数。", file=sys.stderr)
        sys.exit(1)

    # ----- 确定数据源 -----
    file_infos: List[FileImportInfo] = []

    if args.json:
        # 1. JSON 文件
        with open(args.json, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list):
            for item in raw:
                file_infos.append(parse_fileinfo_from_dict(item))
        else:
            file_infos.append(parse_fileinfo_from_dict(raw))
    elif args.files:
        # 2. 命令行文件列表
        for fp in args.files:
            try:
                file_infos.append(create_fileinfo_from_path(fp))
            except Exception as e:
                logger.error("跳过文件 %s: %s", fp, e)
    else:
        # 3. 随机生成
        count = args.count if args.count is not None else 5
        file_infos = [generate_random_fileinfo() for _ in range(count)]

    if not file_infos:
        print("没有可导入的数据。")
        return

    # ----- 相簿关联（如果仓库支持） -----
    target_albums = args.albums or []
    if target_albums:
        try:
            result = repo.batch_import_files(file_infos, target_album_uuids=target_albums)
        except TypeError:
            logger.warning("当前仓库不支持 target_album_uuids，将忽略相簿关联。")
            result = repo.batch_import_files(file_infos)
    else:
        result = repo.batch_import_files(file_infos)

    # ----- 输出结果 -----
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"导入完成: 成功 {result['inserted']}, 跳过 {result['skipped']}")


# ============================================================================
# 子命令：view
# ============================================================================
def cmd_view(args):
    connector = get_connector(args.db)
    view_repo = ViewRepository(connector)
    asset_repo = ViewAssetRepository(connector)

    if args.view_id:
        # 查看特定视图详情（及资产列表）
        view = view_repo.get_view(args.view_id)
        if not view:
            print(f"视图 {args.view_id} 不存在。")
            return

        if not args.list_assets:
            # 仅显示视图概要
            print(f"\n视图: {view.title} (ID: {view.view_id})")
            print(f"类型: {view.view_type.value}")
            print(f"资产数量: {view.asset_count}")
            print(f"封面缩略图: {view.cover_thumb or '无'}")
            return

        # ---- 列出资产 ----
        # 排序字段
        sort_map = {
            "taken_at": AlbumAssetSortOption.TAKEN_AT,
            "added_at": AlbumAssetSortOption.ADDED_AT,
            "sort_order": AlbumAssetSortOption.SORT_ORDER,
        }
        sort_by = sort_map.get(args.sort_by, AlbumAssetSortOption.TAKEN_AT)

        # 分页处理：优先使用 --page，否则用 --offset
        if args.page is not None:
            offset = (args.page - 1) * args.limit
        else:
            offset = args.offset

        # 排序方向（用于输出提示，实际查询可能需要仓库支持）
        order = args.order
        # 注：当前仓库 get_assets 可能不支持 order 参数，此处在展示时告知用户。
        # 如需真正改变排序方向，需要扩展仓库接口或应用层反转列表。
        try:
            assets = asset_repo.get_assets(
                view_id=args.view_id,
                sort_by=sort_by,
                offset=offset,
                limit=args.limit,
            )
        except TypeError:
            # 如果仓库不支持 order 参数，则忽略并调用原始方法
            logger.warning("仓库不支持排序方向参数，将使用默认顺序。")
            assets = asset_repo.get_assets(
                view_id=args.view_id,
                sort_by=sort_by,
                offset=offset,
                limit=args.limit,
            )

        if order == "desc":
            assets = list(reversed(assets))

        # 输出
        if args.json_output:
            output = [
                {
                    "uuid": a.uuid,
                    "media_type": a.media_type,
                    "taken_at": a.taken_at,
                    "is_favorite": a.is_favorite,
                    # "original_name": a.original_name,
                }
                for a in assets
            ]
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(f"\n视图: {view.title} (ID: {view.view_id})")
            print(f"排序: {sort_by.value} ({order}), 偏移: {offset}, 每页: {args.limit}")
            for i, asset in enumerate(assets):
                print(
                    f"  [{offset + i + 1}] {asset.uuid} "
                    f"{asset.media_type} 拍摄: {asset.taken_at} 收藏: {asset.is_favorite}"
                )
    else:
        # 列出所有视图概览
        views = view_repo.get_views()
        if not views:
            print("数据库中没有任何视图。")
            return
        print(f"\n{'视图ID':<30} \t{'标题':<16} \t{'类型':<15} \t{'资产数':<6} \t{'封面'}")
        print("-" * 80)
        for v in views:
            cover = v.cover_thumb if v.cover_thumb else "(无)"
            print(f"{v.view_id:<20} \t{v.title:<12} \t{v.view_type.name:<18} \t{v.asset_count:<6} \t{cover}")


# edit
def cmd_edit(args):
    connector = get_connector(args.db)
    repo = AssetEditRepository(connector)

    if not args.set_fields:
        print("错误：至少需要一个 --set 参数", file=sys.stderr)
        sys.exit(1)

    updates = {}
    for field in args.set_fields:
        if "=" not in field:
            print(f"错误：--set 参数格式必须为 KEY=VALUE，收到: {field}", file=sys.stderr)
            sys.exit(1)
        key, value = field.split("=", 1)
        key = key.strip()
        value = value.strip()

        # 特殊处理 is_favorite
        if key == "is_favorite":
            val_lower = value.lower()
            if val_lower in ("true", "1", "yes"):
                updates[key] = True
            elif val_lower in ("false", "0", "no"):
                updates[key] = False
            else:
                print(f"错误：is_favorite 需要布尔值，收到: {value}", file=sys.stderr)
                sys.exit(1)
        else:
            # 其他字段直接保存为字符串（也尝试转换为数字）
            # 简单处理：如果 value 看起来像数字则转为数字，否则保留字符串
            # 注意 file_size, width, height 应为整数
            if key in ("file_size", "width", "height") and value.isdigit():
                updates[key] = int(value)
            elif key == "exif_json":
                # 不解析，直接作为字符串保存（也可以先验证 JSON 合法性）
                updates[key] = value
            else:
                updates[key] = value

    if not updates:
        print("没有有效的更新字段。")
        sys.exit(1)

    success = repo.update(args.asset_uuid, **updates)
    if success:
        print(f"资产 {args.asset_uuid} 更新成功。")
    else:
        print(f"资产 {args.asset_uuid} 更新失败（UUID 不存在或已删除）。", file=sys.stderr)
        sys.exit(1)


def cmd_get(args):
    connector = get_connector(args.db)
    repo = AssetEditRepository(connector)

    info = repo.debugger_asset_info_get(args.asset_uuid)
    if info is None:
        print(f"资产 {args.asset_uuid} 不存在。", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(info, indent=2, ensure_ascii=False, default=str))


# ============================================================================
# 主入口与参数解析
# ============================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="增强版媒体库 CLI 工具")
    parser.add_argument("--db", default="test_media.db", help="数据库文件路径（默认: test_media.db）")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细日志输出")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---- init ----
    subparsers.add_parser("init", help="初始化数据库（建表+索引）")

    # ---- import ----
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

    # ---- view ----
    view_parser = subparsers.add_parser("view", help="查看视图与资产")
    view_parser.add_argument("--view-id", help="指定视图 ID（不指定则列出所有视图）")
    view_parser.add_argument("--list-assets", action="store_true", help="列出视图内的资产（需指定 --view-id）")
    view_parser.add_argument(
        "--sort-by", choices=["taken_at", "added_at", "sort_order"],
        default="taken_at", help="排序字段（默认: taken_at）"
    )
    view_parser.add_argument(
        "--order", choices=["asc", "desc"], default="desc",
        help="排序方向（默认: desc）"
    )

    # ---- edit ----
    edit_parser = subparsers.add_parser("edit", help="编辑资产的可编辑字段")
    edit_parser.add_argument("asset_uuid", help="目标资产的 UUID")
    edit_parser.add_argument(
        "--set", action="append", dest="set_fields",
        metavar="KEY=VALUE", help="设置字段值（可多次使用）"
    )

    # ---- get ----
    get_parser = subparsers.add_parser("get", help="查看资产完整信息（调试用）")
    get_parser.add_argument("asset_uuid", help="要查询的资产 UUID")
    # 分页参数，优先使用 page
    view_parser.add_argument("--page", type=int, default=None, help="页码（从1开始，优先于 --offset）")
    view_parser.add_argument("--offset", type=int, default=0, help="偏移量（默认: 0）")
    view_parser.add_argument("--limit", type=int, default=50, help="每页数量（默认: 50）")
    view_parser.add_argument("--json-output", action="store_true", help="以 JSON 格式输出资产列表")

    args = parser.parse_args()

    # 日志级别调整
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    # 分发命令
    if args.command == "init":
        cmd_init(args)
    elif args.command == "import":
        cmd_import(args)
    elif args.command == "view":
        cmd_view(args)
    elif args.command == "edit":
        cmd_edit(args)
    elif args.command == "get":
        cmd_get(args)


if __name__ == "__main__":
    main()
