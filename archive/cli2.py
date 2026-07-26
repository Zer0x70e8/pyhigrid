#!/usr/bin/env python3
"""
CLI 测试工具 —— 用于验证 SQLite 数据库连接器、导入仓库、视图仓库和视图资产仓库。

用法：
    # 初始化数据库
    python test_cli.py --db my_media.db init

    # 导入随机测试数据
    python test_cli.py --db my_media.db import --count 10

    # 导入真实文件（支持多个文件路径）
    python test_cli.py --db my_media.db import "E:/path/to/IMG_2967.JPG" "E:/path/to/IMG_2971.JPG"

    # 查看视图
    python test_cli.py --db my_media.db view
    python test_cli.py --db my_media.db view --view-id all_photos --list-assets
"""

import os
import argparse
import hashlib
import logging
import mimetypes
import random
import string
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path


src_path = Path(__file__).parent.parent  # 指向 .../src
sys.path.insert(0, str(src_path))
print("cwd:", os.getcwd())

from albuswall.domain.entities import FileImportInfo
from albuswall.domain.enums import AlbumAssetSortOption
from albuswall.infrastructure.database import Connector
from albuswall.repository.importer import ImportRepository
from albuswall.repository.view import ViewRepository
from albuswall.repository.view_asset import ViewAssetRepository

# ---------------------------------------------------------------------------
# 日志设置
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_cli")


# ============================================================================
# 生成随机导入数据（测试用）
# ============================================================================
def generate_random_fileinfo() -> FileImportInfo:
    """生成随机的 FileImportInfo 用于测试导入"""
    uid = str(uuid.uuid4())
    name = ''.join(random.choices(string.ascii_lowercase, k=8)) + ".jpg"
    path = f"/mock/import/{name}"
    mime = "image/jpeg"
    file_hash = ''.join(random.choices('0123456789abcdef', k=64))
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


# ============================================================================
# 从真实文件生成 FileImportInfo
# ============================================================================
def create_fileinfo_from_path(file_path: str) -> FileImportInfo:
    """根据真实文件路径创建 FileImportInfo 对象"""
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 文件基本信息
    original_name = path.name
    file_size = path.stat().st_size
    mime_type, _ = mimetypes.guess_type(str(path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    # 计算 SHA-256 哈希
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()

    # 文件修改时间作为拍摄日期（粗略处理）
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    taken_at = mtime.isoformat()

    # 生成唯一 uuid
    asset_uuid = str(uuid.uuid4())

    # 缩略图路径留空（实际应由上层服务生成）
    # 宽高暂设为 0，可根据需要集成 PIL 获取真实尺寸
    return FileImportInfo(
        uuid=asset_uuid,
        file_path=str(path),
        original_name=original_name,
        mime_type=mime_type,
        file_hash=file_hash,
        file_size=file_size,
        width=0,
        height=0,
        taken_at=taken_at,
        thumb_path="",
        thumb_small_path="",
        thumb_medium_path="",
    )


# ============================================================================
# 子命令处理
# ============================================================================
def cmd_init(args):
    """初始化数据库（建表 + 索引）"""
    db_path = Path(args.db)
    print(f"正在初始化数据库: {db_path}")
    connector = Connector(db_path)
    try:
        conn = connector.connect()      # 自动建表并创建索引
        conn.close()
        print("数据库初始化成功。")
    except Exception as e:
        logger.error("初始化失败: %s", e)
        sys.exit(1)


def cmd_import(args):
    """导入资产：随机测试数据 或 真实文件"""
    db_path = Path(args.db)
    connector = Connector(db_path)
    repo = ImportRepository(connector)

    if args.files:
        # ----- 导入用户指定的文件 -----
        file_infos = []
        for f in args.files:
            try:
                info = create_fileinfo_from_path(f)
                file_infos.append(info)
                logger.debug("已生成 FileImportInfo: %s", f)
            except Exception as e:
                logger.error("跳过文件 %s: %s", f, e)

        if not file_infos:
            print("没有有效的文件可导入。")
            return

        print(f"正在向 {db_path} 导入 {len(file_infos)} 个文件...")
        result = repo.batch_import_files(file_infos)
        print(f"导入完成: 成功 {result['inserted']}, 跳过 {result['skipped']}")
    else:
        # ----- 生成随机数据导入 -----
        count = args.count
        print(f"正在向 {db_path} 导入 {count} 个随机资产...")
        files = [generate_random_fileinfo() for _ in range(count)]
        result = repo.batch_import_files(files)
        print(f"导入完成: 成功 {result['inserted']}, 跳过 {result['skipped']}")


def cmd_view(args):
    """查看视图和资产"""
    db_path = Path(args.db)
    connector = Connector(db_path)
    view_repo = ViewRepository(connector)
    asset_repo = ViewAssetRepository(connector)

    if args.view_id:
        view = view_repo.get_view(args.view_id)
        if not view:
            print(f"视图 {args.view_id} 不存在。")
            return
        print(f"\n视图: {view.title} (ID: {view.view_id})")
        print(f"类型: {view.view_type.value}")
        print(f"资产数量: {view.asset_count}")
        print(f"封面缩略图: {view.cover_thumb or '无'}")

        if args.list_assets:
            sort_by = AlbumAssetSortOption(args.sort_by)
            assets = asset_repo.get_assets(
                view_id=args.view_id,
                sort_by=sort_by,
                offset=args.offset,
                limit=args.limit
            )
            print(f"\n资产列表 (排序: {sort_by.value}, 偏移: {args.offset}, 限制: {args.limit}):")
            for i, asset in enumerate(assets):
                print(f"  [{i+1}] {asset.uuid[:8]}... {asset.media_type} "
                      f"拍摄: {asset.taken_at} 收藏: {asset.is_favorite}")
    else:
        views = view_repo.get_views()
        if not views:
            print("数据库中没有任何视图。")
            return
        print(f"\n{'视图ID':<30} \t{'标题':<16} \t{'类型':<15} \t{'资产数':<6} \t{'封面'}")
        print("-" * 128)
        for v in views:
            # cover = v.cover_thumb[:30] + "..." if len(v.cover_thumb) > 30 else v.cover_thumb
            # print(f"{v.view_id:<20} {v.title:<12} {v.view_type.value:<15} {v.asset_count:<6} {cover}")
            cover_display = v.cover_thumb if v.cover_thumb else "(无)"
            print(f"{v.view_id:<20} \t{v.title:<12} \t{v.view_type.name:<18} \t{v.asset_count:<6} \t{cover_display}")


# ============================================================================
# 命令行参数解析
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="媒体库数据库测试工具")
    parser.add_argument("--db", default="test_media.db", help="数据库文件路径（默认: test_media.db）")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 子命令: init
    subparsers.add_parser("init", help="初始化数据库（建表+索引）")

    # 子命令: import
    parser_import = subparsers.add_parser("import", help="导入测试资产或真实文件")
    parser_import.add_argument(
        "files", nargs="*", help="要导入的文件路径（可多个）；如果提供则忽略 --count 随机模式"
    )
    parser_import.add_argument(
        "--count", type=int, default=5, help="要导入的随机资产数量（默认: 5，仅在未指定文件时使用）"
    )

    # 子命令: view
    parser_view = subparsers.add_parser("view", help="查看视图和资产")
    parser_view.add_argument("--view-id", type=str, help="指定视图 ID（不指定则列出所有视图）")
    parser_view.add_argument("--list-assets", action="store_true", help="列出视图内的资产")
    parser_view.add_argument("--sort-by", choices=["taken_at", "added_at", "sort_order"],
                             default="taken_at", help="资产排序字段（默认: taken_at）")
    parser_view.add_argument("--offset", type=int, default=0, help="分页偏移（默认: 0）")
    parser_view.add_argument("--limit", type=int, default=50, help="每页数量（默认: 50）")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "import":
        cmd_import(args)
    elif args.command == "view":
        cmd_view(args)


if __name__ == "__main__":
    main()
