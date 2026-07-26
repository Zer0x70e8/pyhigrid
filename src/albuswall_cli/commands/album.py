#
"""相簿管理子命令"""
import sys
import json
import logging
from pathlib import Path

from albuswall.domain.enums import AlbumType
from albuswall.infrastructure.database import Connector
from albuswall.repository.album import AlbumRepository

logger = logging.getLogger(__name__)


def register(subparsers):
    """注册 album 子命令及其子命令组"""
    album_parser = subparsers.add_parser("album", help="管理相簿")
    album_subs = album_parser.add_subparsers(dest="album_action", required=True)

    # ---- create ----
    create_parser = album_subs.add_parser("create", help="创建相簿")
    create_parser.add_argument("--title", required=True, help="相簿标题")
    create_parser.add_argument(
        "--type", choices=["manual", "smart"], default="manual",
        help="相簿类型（默认: manual）"
    )
    create_parser.add_argument("--cover-asset-id", type=int, help="封面资产的数据库 ID")
    create_parser.add_argument("--sort-order", type=int, default=0, help="排序值")
    create_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    # ---- update ----
    update_parser = album_subs.add_parser("update", help="更新相簿属性")
    update_parser.add_argument("album_uuid", help="相簿 UUID")
    update_parser.add_argument("--title", help="新标题")
    update_parser.add_argument("--type", choices=["manual", "smart"], help="相簿类型")
    update_parser.add_argument("--cover-asset-id", type=int, help="封面资产 ID")
    update_parser.add_argument("--sort-order", type=int, help="排序值")
    update_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    # ---- get ----
    get_parser = album_subs.add_parser("get", help="查看相簿详情")
    get_parser.add_argument("album_uuid", help="相簿 UUID")
    get_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    # ---- add-assets ----
    add_parser = album_subs.add_parser("add-assets", help="将资产添加到相簿")
    add_parser.add_argument("album_uuid", help="目标相簿 UUID")
    add_parser.add_argument("asset_uuids", nargs="+", help="一个或多个资产 UUID")

    # ---- remove-assets ----
    remove_parser = album_subs.add_parser("remove-assets", help="从相簿移除资产")
    remove_parser.add_argument("album_uuid", help="目标相簿 UUID")
    remove_parser.add_argument("asset_uuids", nargs="+", help="一个或多个资产 UUID")

    # ---- list ----
    list_parser = album_subs.add_parser("list", help="列出所有相簿")
    list_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    album_parser.set_defaults(func=run)


def run(args):
    """分发 album 子命令"""
    connector = Connector(Path(args.db))
    repo = AlbumRepository(connector)

    action = args.album_action

    if action == "create":
        album_type = AlbumType.MANUAL if args.type == "manual" else AlbumType.SMART
        album = repo.create_album(
            title=args.title,
            album_type=album_type,
            cover_asset_id=args.cover_asset_id,
            sort_order=args.sort_order,
        )
        _print_album(album, args.json)

    elif action == "update":
        updates = {}
        if args.title is not None:
            updates["title"] = args.title
        if args.type is not None:
            updates["album_type"] = AlbumType.MANUAL if args.type == "manual" else AlbumType.SMART
        if args.cover_asset_id is not None:
            updates["cover_asset_id"] = args.cover_asset_id
        if args.sort_order is not None:
            updates["sort_order"] = args.sort_order

        if not updates:
            print("没有提供要更新的字段。")
            return

        try:
            album = repo.update_album(args.album_uuid, **updates)
            _print_album(album, args.json)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

    elif action == "get":
        album = repo.get_album(args.album_uuid)
        if album is None:
            print(f"相簿 {args.album_uuid} 不存在。", file=sys.stderr)
            sys.exit(1)
        _print_album(album, args.json)

    elif action == "add-assets":
        try:
            count = repo.add_assets_to_album(args.asset_uuids, args.album_uuid)
            print(f"成功添加 {count} 个资产到相簿 {args.album_uuid}。")
        except ValueError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

    elif action == "remove-assets":
        count = repo.remove_assets_from_album(args.asset_uuids, args.album_uuid)
        print(f"从相簿 {args.album_uuid} 移除了 {count} 个资产。")

    elif action == "list":
        albums = repo.list_albums(order_by="sort_order")
        if not albums:
            print("没有任何相簿。")
            return

        if args.json:
            print(json.dumps(
                [{
                    "uuid": a.uuid,
                    "title": a.title,
                    "album_type": a.album_type.name,
                    "cover_asset_id": a.cover_asset_id,
                    "sort_order": a.sort_order,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "modified_at": a.modified_at.isoformat() if a.modified_at else None,
                } for a in albums],
                ensure_ascii=False, indent=2
            ))
        else:
            print(f"\n{'UUID':<38} {'标题':<16} {'类型':<10} {'封面ID':<8} {'排序':<6}")
            print("-" * 80)
            for a in albums:
                print(
                    f"{a.uuid:<38} {a.title:<16} {a.album_type.name:<10} "
                    f"{a.cover_asset_id or '':<8} {a.sort_order:<6}"
                )


def _print_album(album, as_json=False):
    """格式化输出相簿对象"""
    if album is None:
        print("相簿不存在。")
        return

    data = {
        "uuid": album.uuid,
        "title": album.title,
        "album_type": album.album_type.name,
        "cover_asset_id": album.cover_asset_id,
        "sort_order": album.sort_order,
        "created_at": album.created_at.isoformat() if album.created_at else None,
        "modified_at": album.modified_at.isoformat() if album.modified_at else None,
    }

    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"UUID: {data['uuid']}")
        print(f"标题: {data['title']}")
        print(f"类型: {data['album_type']}")
        print(f"封面资产ID: {data['cover_asset_id']}")
        print(f"排序值: {data['sort_order']}")
        print(f"创建时间: {data['created_at']}")
        print(f"修改时间: {data['modified_at']}")
