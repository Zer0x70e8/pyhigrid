#
"""编辑资产子命令"""
import sys
import logging
from pathlib import Path

from pyhigrid.infrastructure.database import Connector
from pyhigrid.repository.asset_edit import AssetEditRepository

logger = logging.getLogger(__name__)


def register(subparsers):
    """注册 edit 子命令到 argparse subparsers"""
    parser = subparsers.add_parser("edit", help="编辑资产的可编辑字段")
    parser.add_argument("asset_uuid", help="目标资产的 UUID")
    parser.add_argument(
        "--set", action="append", dest="set_fields",
        metavar="KEY=VALUE", help="设置字段值（可多次使用）"
    )
    # 便捷标志：收藏 / 取消收藏
    fav_group = parser.add_mutually_exclusive_group()
    fav_group.add_argument(
        "--favorite", action="store_true", dest="set_favorite",
        help="设为收藏"
    )
    fav_group.add_argument(
        "--unfavorite", action="store_true", dest="set_unfavorite",
        help="取消收藏"
    )
    parser.set_defaults(func=run)


def run(args):
    """执行 edit 命令"""
    connector = Connector(Path(args.db))
    repo = AssetEditRepository(connector)

    # 收集通过 --set 指定的字段
    updates = {}
    if args.set_fields:
        for field in args.set_fields:
            if "=" not in field:
                print(f"错误：--set 参数格式必须为 KEY=VALUE，收到: {field}", file=sys.stderr)
                sys.exit(1)
            key, value = field.split("=", 1)
            key = key.strip()
            value = value.strip()

            # 特殊处理 is_favorite 布尔值
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
                # 尝试转换为数字（针对已知的整数字段）
                if key in ("file_size", "width", "height") and value.isdigit():
                    updates[key] = int(value)
                elif key == "exif_json":
                    updates[key] = value
                else:
                    updates[key] = value

    # 处理便捷标志
    if args.set_favorite:
        if "is_favorite" in updates and not updates["is_favorite"]:
            print("错误：--favorite 与 --set is_favorite=false 冲突", file=sys.stderr)
            sys.exit(1)
        updates["is_favorite"] = True
    if args.set_unfavorite:
        if "is_favorite" in updates and updates["is_favorite"]:
            print("错误：--unfavorite 与 --set is_favorite=true 冲突", file=sys.stderr)
            sys.exit(1)
        updates["is_favorite"] = False

    if not updates:
        print("没有有效的更新字段。")
        sys.exit(1)

    success = repo.update(args.asset_uuid, **updates)
    if success:
        print(f"资产 {args.asset_uuid} 更新成功。")
    else:
        print(f"资产 {args.asset_uuid} 更新失败（UUID 不存在或已删除）。", file=sys.stderr)
        sys.exit(1)
