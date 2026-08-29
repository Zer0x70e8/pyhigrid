#
"""
source 子命令：管理导入源配置。
支持 add / list / show / update / delete 操作。
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

from albuswall.infrastructure.database import Connector
from albuswall.repositories.ingest_source import IngestSourceRepository

logger = logging.getLogger(__name__)


def register(subparsers: argparse._SubParsersAction) -> None:
    """注册 source 子命令及其下级子命令到主解析器。"""
    source_parser = subparsers.add_parser(
        "source", help="管理导入源配置"
    )
    source_subparsers = source_parser.add_subparsers(dest="source_action", required=True)

    # source list
    list_parser = source_subparsers.add_parser("list", help="列出所有导入源")
    list_parser.set_defaults(func=run_list)

    # source show <id>
    show_parser = source_subparsers.add_parser("show", help="显示指定导入源的详细信息")
    show_parser.add_argument("id", type=int, help="导入源 ID")
    show_parser.set_defaults(func=run_show)

    # source add
    add_parser = source_subparsers.add_parser("add", help="新增导入源")
    _add_common_arguments(add_parser, required_fields={"title", "source_path"})
    add_parser.set_defaults(func=run_add)

    # source update <id>
    update_parser = source_subparsers.add_parser("update", help="更新导入源配置")
    update_parser.add_argument("id", type=int, help="要更新的导入源 ID")
    _add_common_arguments(update_parser, required_fields=set())
    update_parser.set_defaults(func=run_update)

    # source delete <id>
    delete_parser = source_subparsers.add_parser("delete", help="删除导入源")
    delete_parser.add_argument("id", type=int, help="要删除的导入源 ID")
    delete_parser.add_argument("--yes", "-y", action="store_true", help="跳过确认提示")
    delete_parser.set_defaults(func=run_delete)


def _add_common_arguments(parser: argparse.ArgumentParser, required_fields: set) -> None:
    """为 add / update 子命令添加通用字段参数。"""
    # 必填字段
    parser.add_argument("--title", required=("title" in required_fields), help="导入源标题")
    parser.add_argument(
        "--source-path",
        required=("source_path" in required_fields),
        help="源文件/目录路径",
    )

    # 可选字段
    parser.add_argument("--description", help="描述信息")
    parser.add_argument("--target-path", help="目标路径")
    parser.add_argument("--mount-point", help="挂载点")
    parser.add_argument(
        "--auto-mount",
        dest="auto_mount",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="是否自动挂载",
    )
    parser.add_argument(
        "--file-type-check",
        choices=["none", "extension", "mime"],
        default=None,
        help="文件类型检查方式",
    )
    parser.add_argument(
        "--file-types",
        type=json.loads,
        default=None,
        help='允许的文件类型（JSON 数组，例如 \'[".txt", ".md"]\'）',
    )
    parser.add_argument(
        "--tags",
        type=json.loads,
        default=None,
        help='标签列表（JSON 数组，例如 \'["docs", "important"]\'）',
    )
    parser.add_argument(
        "--subfolder-recursion",
        dest="subfolder_recursion",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="是否递归子文件夹",
    )
    parser.add_argument(
        "--subfolder-recursion-depth",
        type=int,
        default=None,
        help="递归深度（0 表示无限制）",
    )
    parser.add_argument(
        "--trigger-config",
        type=json.loads,
        default=None,
        help='触发配置（JSON 对象，例如 \'{"type": "watch"}\'）',
    )


def _build_repo(args) -> IngestSourceRepository:
    """根据命令行参数建立数据库连接并返回仓库实例。"""
    db_path = Path(args.db)
    connector = Connector(str(db_path))
    # conn = connector.connect()  # 自动建表/索引
    connector.connect()  # 自动建表/索引
    return IngestSourceRepository(connector)


def _print_source(source: Dict[str, Any]) -> None:
    """友好地打印一条导入源记录。"""
    print(f"ID: {source['id']}")
    print(f"  标题: {source.get('title', '')}")
    print(f"  源路径: {source.get('source_path', '')}")
    if source.get("description"):
        print(f"  描述: {source['description']}")
    if source.get("target_path"):
        print(f"  目标路径: {source['target_path']}")
    if source.get("mount_point"):
        print(f"  挂载点: {source['mount_point']}")
    auto_mount = "是" if source.get("auto_mount") else "否"
    print(f"  自动挂载: {auto_mount}")
    if source.get("file_type_check"):
        print(f"  文件类型检查: {source['file_type_check']}")
    if source.get("file_types"):
        print(f"  文件类型: {', '.join(source['file_types'])}")
    if source.get("tags"):
        print(f"  标签: {', '.join(source['tags'])}")
    if source.get("subfolder_recursion") is not None:
        recursion = "是" if source["subfolder_recursion"] else "否"
        print(f"  递归子文件夹: {recursion}")
    if source.get("subfolder_recursion_depth") is not None:
        print(f"  递归深度: {source['subfolder_recursion_depth']}")
    if source.get("trigger_config"):
        print(f"  触发配置: {json.dumps(source['trigger_config'], ensure_ascii=False)}")
    print()


# ----------------------------------------------------------------------
# 子命令处理函数
# ----------------------------------------------------------------------
def run_list(args) -> None:
    """处理 source list：列出所有导入源。"""
    repo = _build_repo(args)
    sources = repo.get_all()
    if not sources:
        print("暂无导入源配置。")
        return
    print(f"共 {len(sources)} 条导入源：")
    for source in sources:
        _print_source(source)


def run_show(args) -> None:
    """处理 source show <id>：显示指定导入源详情。"""
    repo = _build_repo(args)
    source = repo.get_by_id(args.id)
    if source is None:
        print(f"错误：ID 为 {args.id} 的导入源不存在。")
        sys.exit(1)
    _print_source(source)


def run_add(args) -> None:
    """处理 source add：新增导入源。"""
    repo = _build_repo(args)
    # 收集非 None 的参数
    fields = {
        "title": args.title,
        "source_path": args.source_path,
        "description": args.description,
        "target_path": args.target_path,
        "mount_point": args.mount_point,
        "auto_mount": args.auto_mount,
        "file_type_check": args.file_type_check,
        "file_types": args.file_types,
        "tags": args.tags,
        "subfolder_recursion": args.subfolder_recursion,
        "subfolder_recursion_depth": args.subfolder_recursion_depth,
        "trigger_config": args.trigger_config,
    }
    # 过滤掉 None 值（保留 False、0、空字符串等有效值）
    payload = {k: v for k, v in fields.items() if v is not None}

    try:
        new_id = repo.create(**payload)
        print(f"成功创建导入源，ID = {new_id}")
    except Exception as e:
        logger.error("创建失败: %s", e)
        print(f"错误：{e}")
        sys.exit(1)


def run_update(args) -> None:
    """处理 source update <id>：更新导入源配置。"""
    repo = _build_repo(args)
    # 收集所有可能更新的字段（排除 id 和 func）
    fields = {
        "title": args.title,
        "description": args.description,
        "source_path": args.source_path,
        "target_path": args.target_path,
        "mount_point": args.mount_point,
        "auto_mount": args.auto_mount,
        "file_type_check": args.file_type_check,
        "file_types": args.file_types,
        "tags": args.tags,
        "subfolder_recursion": args.subfolder_recursion,
        "subfolder_recursion_depth": args.subfolder_recursion_depth,
        "trigger_config": args.trigger_config,
    }
    # 过滤掉 None 值
    payload = {k: v for k, v in fields.items() if v is not None}

    if not payload:
        print("未提供任何要更新的字段。")
        sys.exit(1)

    try:
        updated = repo.update(args.id, **payload)
        if updated:
            print(f"成功更新 ID 为 {args.id} 的导入源。")
        else:
            print(f"警告：ID 为 {args.id} 的导入源不存在或未发生任何变更。")
    except Exception as e:
        logger.error("更新失败: %s", e)
        print(f"错误：{e}")
        sys.exit(1)


def run_delete(args) -> None:
    """处理 source delete <id>：删除导入源。"""
    if not args.yes:
        confirm = input(f"确定要删除 ID 为 {args.id} 的导入源吗？[y/N] ")
        if confirm.lower() not in ("y", "yes"):
            print("已取消删除。")
            return

    repo = _build_repo(args)
    try:
        deleted = repo.delete(args.id)
        if deleted:
            print(f"成功删除 ID 为 {args.id} 的导入源。")
        else:
            print(f"错误：ID 为 {args.id} 的导入源不存在。")
            sys.exit(1)
    except Exception as e:
        logger.error("删除失败: %s", e)
        print(f"错误：{e}")
        sys.exit(1)
