#
"""初始化数据库子命令"""
import sys
import logging
from pathlib import Path

from pyhigrid.infrastructure.database import Connector

logger = logging.getLogger(__name__)


def register(subparsers):
    """注册 init 子命令到 argparse subparsers"""
    init_parser = subparsers.add_parser("init", help="初始化数据库（建表+索引）")
    init_parser.set_defaults(func=run)

def run(args):
    """执行 init 命令"""
    db_path = Path(args.db)
    logger.info("正在初始化数据库: %s", db_path)
    connector = Connector(db_path)
    try:
        conn = connector.connect()  # 自动建表/索引
        conn.close()
        logger.info("数据库初始化成功。")
    except Exception as e:
        logger.error("初始化失败: %s", e)
        sys.exit(1)
