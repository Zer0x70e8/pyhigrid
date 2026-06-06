#!/usr/bin/env python3
"""
媒体库 CLI 主入口
负责参数解析、子命令注册与分发
"""
import argparse
import logging

if __name__ == '__main__':
    import sys
    from pathlib import Path

    # 添加项目 src 路径，保证导入 pyhigrid
    src_path = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(src_path))

from pyhigrid_cli.config import DEFAULT_DB, setup_logging
from pyhigrid_cli.commands import register_all

logger = logging.getLogger(__name__)
# logging.getLogger("__main__").setLevel(logging.DEBUG)


def main():
    parser = argparse.ArgumentParser(description="simple album CLI tool")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"db path(default: {DEFAULT_DB})")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细日志输出")

    subparsers = parser.add_subparsers(dest="command", required=True)
    register_all(subparsers)   # 注册所有子命令，并绑定 lazy_func

    args = parser.parse_args()
    setup_logging(args.verbose)

    # 直接调用由 set_defaults 绑定的延迟函数
    args.func(args)


if __name__ == "__main__":
    main()
