#
"""
trigger 子命令：管理导入源的触发器配置。
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from albuswall.infrastructure.database import Connector
from albuswall.repositories.ingest_source import IngestSourceRepository

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 辅助函数
# ----------------------------------------------------------------------
def str2bool(value: str) -> bool:
    """将命令行字符串转换为布尔值。"""
    if isinstance(value, bool):
        return value
    if value.lower() in ("yes", "true", "t", "y", "1"):
        return True
    if value.lower() in ("no", "false", "f", "n", "0"):
        return False
    raise argparse.ArgumentTypeError(f"无效的布尔值: {value!r}")


def get_repository(db_path: Path) -> IngestSourceRepository:
    """根据数据库路径创建并返回 IngestSourceRepository 实例。"""
    connector = Connector(str(db_path))
    repo = IngestSourceRepository(connector)
    return repo


def print_trigger(source_id: int, trigger_config: Optional[Dict[str, Any]]) -> None:
    """格式化输出 trigger 配置。"""
    if not trigger_config:
        print(f"源 {source_id} 没有配置触发器。")
        return
    print(f"触发器配置 (源 ID: {source_id}):")
    print(json.dumps(trigger_config, indent=2, ensure_ascii=False))


# ----------------------------------------------------------------------
# 子命令处理函数
# ----------------------------------------------------------------------
def show_trigger(args: argparse.Namespace) -> None:
    """显示指定导入源的触发器配置。"""
    repo = get_repository(Path(args.db))
    source = repo.get_by_id(args.source_id)
    if source is None:
        logger.error("源 ID %s 不存在。", args.source_id)
        sys.exit(1)
    trigger_config = source.get("trigger_config")
    print_trigger(args.source_id, trigger_config)


def set_trigger(args: argparse.Namespace) -> None:
    """设置或更新指定导入源的触发器配置。"""
    repo = get_repository(Path(args.db))
    source = repo.get_by_id(args.source_id)
    if source is None:
        logger.error("源 ID %s 不存在。", args.source_id)
        sys.exit(1)

    # 获取现有 trigger_config（可能为 None 或 dict）
    existing_config = source.get("trigger_config") or {}

    # 构建要更新的字段字典，仅包含显式提供的参数
    updates: Dict[str, Any] = {}
    field_names = [
        "scheduled_enabled",
        "update_mode",
        "scheduled_time",
        "interval_time",
        "device_trigger_enabled",
        "target",
        "auto_mount",
        "mount_point",
    ]
    for field in field_names:
        value = getattr(args, field, None)
        if value is not None:
            updates[field] = value

    if not updates:
        logger.warning("未提供任何要更新的字段。")
        return

    # 合并配置
    new_config = {**existing_config, **updates}

    # 更新数据库
    success = repo.update(args.source_id, trigger_config=new_config)
    if success:
        logger.info("触发器配置已更新。")
        print_trigger(args.source_id, new_config)
    else:
        logger.error("更新失败，可能源不存在或数据库错误。")
        sys.exit(1)


def unset_trigger(args: argparse.Namespace) -> None:
    """删除指定导入源的整个触发器配置或指定字段。"""
    repo = get_repository(Path(args.db))
    source = repo.get_by_id(args.source_id)
    if source is None:
        logger.error("源 ID %s 不存在。", args.source_id)
        sys.exit(1)

    existing_config = source.get("trigger_config") or {}

    if args.field:
        # 删除指定字段
        field = args.field
        if field not in existing_config:
            logger.warning("字段 %s 不存在于触发器中。", field)
            return
        new_config = existing_config.copy()
        del new_config[field]
    else:
        # 删除整个触发器配置（设为空字典）
        new_config = {}

    success = repo.update(args.source_id, trigger_config=new_config)
    if success:
        logger.info("触发器配置已更新。")
        print_trigger(args.source_id, new_config)
    else:
        logger.error("更新失败。")
        sys.exit(1)


def list_triggers(args: argparse.Namespace) -> None:
    """列出所有导入源的触发器摘要。"""
    repo = get_repository(Path(args.db))
    sources = repo.get_all()
    if not sources:
        print("没有找到任何导入源。")
        return

    print(f"{'ID':<5} {'标题':<30} {'定时启用':<10} {'设备启用':<10}")
    print("-" * 60)
    for src in sources:
        trigger = src.get("trigger_config") or {}
        scheduled = "是" if trigger.get("scheduled_enabled") else "否"
        device = "是" if trigger.get("device_trigger_enabled") else "否"
        print(f"{src['id']:<5} {src.get('title', ''):<30} {scheduled:<10} {device:<10}")


# ----------------------------------------------------------------------
# 注册子命令
# ----------------------------------------------------------------------
def register(subparsers):
    """注册 trigger 子命令到 argparse subparsers"""
    trigger_parser = subparsers.add_parser(
        "trigger",
        help="管理导入源的触发器配置",
        description="对 ingest_source 表的 trigger_config 字段进行查看、设置、删除或列出操作。",
    )
    trigger_subparsers = trigger_parser.add_subparsers(dest="trigger_command", required=True)

    # show 子命令
    show_parser = trigger_subparsers.add_parser("show", help="显示指定源的触发器配置")
    show_parser.add_argument("source_id", type=int, help="导入源 ID")
    show_parser.set_defaults(func=show_trigger)

    # set 子命令
    set_parser = trigger_subparsers.add_parser("set", help="设置或更新触发器配置")
    set_parser.add_argument("source_id", type=int, help="导入源 ID")
    set_parser.add_argument(
        "--scheduled-enabled",
        type=str2bool,
        help="是否启用定时触发器 (true/false)",
    )
    set_parser.add_argument("--update-mode", help="更新模式 (如 replace, merge 等)")
    set_parser.add_argument("--scheduled-time", help="定时触发时间 (格式由应用定义)")
    set_parser.add_argument("--interval-time", help="间隔触发时间")
    set_parser.add_argument(
        "--device-trigger-enabled",
        type=str2bool,
        help="是否启用设备触发器 (true/false)",
    )
    set_parser.add_argument("--target", help="设备触发器目标路径")
    set_parser.add_argument(
        "--auto-mount",
        type=str2bool,
        help="设备触发器是否自动挂载 (true/false)",
    )
    set_parser.add_argument("--mount-point", help="挂载点")
    set_parser.set_defaults(func=set_trigger)

    # unset 子命令
    unset_parser = trigger_subparsers.add_parser(
        "unset", help="删除触发器配置或指定字段"
    )
    unset_parser.add_argument("source_id", type=int, help="导入源 ID")
    unset_parser.add_argument(
        "--field",
        help="要删除的字段名（如果不指定则删除整个触发器配置）",
    )
    unset_parser.set_defaults(func=unset_trigger)

    # list 子命令
    list_parser = trigger_subparsers.add_parser(
        "list", help="列出所有导入源的触发器摘要"
    )
    list_parser.set_defaults(func=list_triggers)


# ----------------------------------------------------------------------
# 主入口（由主 CLI 调用）
# ----------------------------------------------------------------------
def run(args: argparse.Namespace) -> None:
    """执行 trigger 子命令（由主解析器分发）。"""
    # args.func 已经由子命令的 set_defaults 设置
    args.func(args)