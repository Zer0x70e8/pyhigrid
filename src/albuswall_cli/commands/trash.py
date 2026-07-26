#
"""回收站管理子命令"""
import sys
import time
import logging
from pathlib import Path

from albuswall.infrastructure.database import Connector
from albuswall.repository.trash import TrashRepository

logger = logging.getLogger(__name__)


def register(subparsers):
    """注册 trash 命令，直接包含资产回收操作和相簿永久删除"""
    trash_parser = subparsers.add_parser("trash", help="管理回收站（资产）与删除相簿")
    trash_subs = trash_parser.add_subparsers(dest="action", required=True)

    # ---- 资产回收站操作 ----
    delete_parser = trash_subs.add_parser("delete", help="软删除资产（移入回收站）")
    delete_parser.add_argument("uuids", nargs="+", metavar="UUID")

    restore_parser = trash_subs.add_parser("restore", help="恢复已删除资产")
    restore_parser.add_argument("uuids", nargs="+", metavar="UUID")

    purge_parser = trash_subs.add_parser("purge", help="永久删除资产（不可恢复）")
    purge_parser.add_argument("uuids", nargs="+", metavar="UUID")

    empty_parser = trash_subs.add_parser("empty", help="清空资产回收站")
    empty_parser.add_argument("--yes", action="store_true", help="跳过确认提示")

    trash_subs.add_parser("list", help="列出已删除资产")

    # ---- 相簿删除（直接永久删除）----
    album_delete_parser = trash_subs.add_parser("delete-album", help="永久删除相簿（不可恢复）")
    album_delete_parser.add_argument("album_uuid", metavar="ALBUM_UUID")

    trash_parser.set_defaults(func=run)


def _show_progress(label="处理中", total=100, delay=0.02):
    """显示简单的进度条"""
    for i in range(total + 1):
        sys.stdout.write(f"\r{label}: {i}%")
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")


def run(args):
    connector = Connector(Path(args.db))
    repo = TrashRepository(connector)

    action = args.action  # delete, restore, purge, empty, list, delete_album

    # =================== 资产操作 ===================
    if action == "delete":
        # 明确提示这是资产回收操作
        print("注意：即将对资产执行软删除（回收），操作后可通过 trash restore 恢复。")
        count = repo.soft_delete_assets(args.uuids)
        print(f"已软删除 {count} 个资产。")

    elif action == "restore":
        count = repo.restore_assets(args.uuids)
        print(f"已恢复 {count} 个资产。")

    elif action == "purge":
        confirm = input("永久删除资产将不可恢复，确认吗？(yes/no): ")
        if confirm.lower() != "yes":
            print("已取消。")
            return
        count = repo.permanently_delete_assets(args.uuids)
        print(f"已永久删除 {count} 个资产。")

    elif action == "empty":
        if not args.yes:
            confirm = input("确认清空资产回收站吗？此操作不可逆！(yes/no): ")
            if confirm.lower() != "yes":
                print("已取消。")
                return
        conn = connector.connect()
        rows = conn.execute(
            "SELECT uuid FROM assets WHERE is_deleted = 1"
        ).fetchall()
        uuids = [r["uuid"] for r in rows]
        if uuids:
            repo.permanently_delete_assets(uuids)
            print(f"已永久删除 {len(uuids)} 个资产。")
        else:
            print("资产回收站为空。")
        conn.close()

    elif action == "list":
        conn = connector.connect()
        rows = conn.execute(
            "SELECT uuid, original_name FROM assets WHERE is_deleted = 1"
        ).fetchall()
        if rows:
            print("已删除资产列表:")
            for r in rows:
                print(f"  {r['uuid']}  {r['original_name']}")
        else:
            print("资产回收站为空。")
        conn.close()

    # =================== 相簿操作 ===================
    elif action == "delete_album":
        album_uuid = args.album_uuid
        print(f"即将永久删除相簿 {album_uuid}，此操作不可逆！")
        confirm = input("确认删除？(yes/no): ")
        if confirm.lower() != "yes":
            print("已取消。")
            return
        try:
            _show_progress("正在删除相簿", total=100, delay=0.02)
            ok = repo.permanently_delete_album(album_uuid)
            if ok:
                print(f"相簿 {album_uuid} 已永久删除。")
            else:
                print("错误: 相簿不存在或已删除。", file=sys.stderr)
                sys.exit(1)
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
