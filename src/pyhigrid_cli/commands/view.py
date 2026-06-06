#
"""视图查看子命令"""
import json
import logging
from pathlib import Path

from pyhigrid.domain.enums import AlbumAssetSortOption
from pyhigrid.infrastructure.database import Connector
from pyhigrid.repository.view import ViewRepository
from pyhigrid.repository.view_asset import ViewAssetRepository

logger = logging.getLogger(__name__)


def register(subparsers):
    """注册 view 子命令到 argparse subparsers"""
    view_parser = subparsers.add_parser("view", help="查看视图与资产")
    view_parser.add_argument("--view-id", help="指定视图 ID（不指定则列出所有视图）")
    view_parser.add_argument(
        "--list-assets", action="store_true",
        help="列出视图内的资产（需指定 --view-id）"
    )
    view_parser.add_argument(
        "--sort-by", choices=["taken_at", "added_at", "sort_order"],
        default="taken_at", help="排序字段（默认: taken_at）"
    )
    view_parser.add_argument(
        "--order", choices=["asc", "desc"], default="desc",
        help="排序方向（默认: desc）"
    )
    # 分页参数，优先使用 page
    view_parser.add_argument(
        "--page", type=int, default=None,
        help="页码（从1开始，优先于 --offset）"
    )
    view_parser.add_argument(
        "--offset", type=int, default=0,
        help="偏移量（默认: 0）"
    )
    view_parser.add_argument(
        "--limit", type=int, default=50,
        help="每页数量（默认: 50）"
    )
    view_parser.add_argument(
        "--json-output", action="store_true",
        help="以 JSON 格式输出资产列表"
    )
    view_parser.set_defaults(func=run)


def run(args):
    """执行 view 命令"""
    connector = Connector(Path(args.db))
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
        # 排序字段映射
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

        order = args.order

        # 尝试获取资产，若仓库不支持 order 参数则忽略
        try:
            assets = asset_repo.get_assets(
                view_id=args.view_id,
                sort_by=sort_by,
                offset=offset,
                limit=args.limit,
            )
        except TypeError:
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
