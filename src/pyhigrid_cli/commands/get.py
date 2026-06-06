#
"""查看资产详细信息子命令"""
import sys
import json
import logging
from pathlib import Path

from pyhigrid.infrastructure.database import Connector
from pyhigrid.repository.asset_edit import AssetEditRepository

logger = logging.getLogger(__name__)


def register(subparsers):
    """注册 get 子命令到 argparse subparsers"""
    parser = subparsers.add_parser("get", help="查看资产完整信息（调试用）")
    parser.add_argument("asset_uuid", help="要查询的资产 UUID")
    parser.set_defaults(func=run)


def run(args):
    """执行 get 命令"""
    connector = Connector(Path(args.db))
    repo = AssetEditRepository(connector)

    info = repo.debugger_asset_info_get(args.asset_uuid)
    if info is None:
        print(f"资产 {args.asset_uuid} 不存在。", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(info, indent=2, ensure_ascii=False, default=str))
