#
"""触发器服务管理子命令"""

import time
import logging
from pathlib import Path

from albuswall.infrastructure.database import Connector
from albuswall.repositories import IngestSourceRepository
from albuswall.services.trigger.core import TriggerService

logger = logging.getLogger(__name__)


def register(subparsers):
    """注册 trigger_service 子命令到 argparse subparsers"""
    parser = subparsers.add_parser(
        "trigger_service",
        help="管理触发器服务（start/status/list/show/update/test）"
    )
    sub = parser.add_subparsers(dest="action", required=True)

    # 子命令：start
    sub_start = sub.add_parser("start", help="启动触发器调度服务（前台）")
    sub_start.set_defaults(func=run_start)

    # 子命令：status
    sub_status = sub.add_parser("status", help="显示服务心跳状态")
    sub_status.set_defaults(func=run_status)

    # 子命令：list
    sub_list = sub.add_parser("list", help="列出当前加载的触发器和回调详情（不强制重新加载）")
    sub_list.set_defaults(func=run_list)

    # 子命令：show
    sub_show = sub.add_parser("show", help="强制重新加载触发器、清理孤儿回调，并显示完整状态")
    sub_show.set_defaults(func=run_show)

    # 子命令：update
    sub_update = sub.add_parser("update", help="从数据库重新加载触发器")
    sub_update.set_defaults(func=run_update)

    # 子命令：test（新增）
    sub_test = sub.add_parser("test", help="测试触发器调度：注册回调并运行一段时间，统计触发次数")
    sub_test.add_argument(
        "-d", "--duration",
        type=int,
        default=10,
        help="测试持续时间（秒），默认10秒"
    )
    sub_test.add_argument(
        "--source-id",
        type=str,
        default=None,
        help="只测试指定 source_id 的触发器，不指定则测试所有"
    )
    sub_test.add_argument(
        "--verbose",
        action="store_true",
        help="打印每次触发的详细信息"
    )
    sub_test.set_defaults(func=run_test)


def run_test(args):
    """执行 test 子命令：启动服务并统计触发器回调次数"""
    import threading
    import time

    db_path = Path(args.db)
    service, conn = _create_service(db_path)

    # 获取所有计划触发器 source_id（直接读取私有属性，测试环境可接受）
    with service._lock:
        scheduled_ids = [meta["source_id"] for meta, _ in service._scheduled_triggers]

    if not scheduled_ids:
        print("没有找到任何计划触发器，无法测试。")
        conn.close()
        return

    # 如果指定了 source_id，检查是否存在
    if args.source_id and args.source_id not in scheduled_ids:
        print(f"找不到 source_id={args.source_id} 的触发器。")
        conn.close()
        return

    # 准备回调计数
    counts = {}
    lock = threading.Lock()
    def make_callback(sid):
        def callback():
            with lock:
                counts[sid] = counts.get(sid, 0) + 1
            if args.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] 触发器触发：source_id={sid}")
        return callback

    # 注册回调
    for sid in scheduled_ids:
        if args.source_id and sid != args.source_id:
            continue
        service.add_scheduled_callback(str(sid), make_callback(sid))
        counts[sid] = 0

    # 启动服务
    service.start()
    print(f"测试开始，等待 {args.duration} 秒...")
    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("测试被用户中断")
    finally:
        service.stop()
        conn.close()

    # 输出结果
    print("\n测试结果：")
    if not counts:
        print("没有回调被触发。")
    else:
        for sid, count in counts.items():
            print(f"  source_id={sid}: 触发 {count} 次")
        if all(v == 0 for v in counts.values()):
            print("提示：所有触发器均未触发，请检查触发器配置（cron 表达式或间隔时间）是否正确。")


def run_show(args):
    """执行 show 子命令：重新加载触发器，清理孤儿回调，然后打印 __str__ 输出"""
    db_path = Path(args.db)
    service, conn = _create_service(db_path)
    try:
        # 从数据库完整重新加载所有触发器
        service.update_triggers()
        # 清理所有失去触发器的回调
        cleaned = service.clean_orphan_callbacks()
        if cleaned:
            print(f"已清理 {cleaned} 个孤儿回调组")
        print("数据完整加载后的状态：")
        print(str(service))
    finally:
        conn.close()


def _create_service(db_path: Path):
    """根据数据库路径创建 TriggerService 实例"""
    connector = Connector(str(db_path))
    conn = connector.connect()
    repo = IngestSourceRepository(connector)
    service = TriggerService(repo)
    return service, conn


def run_start(args):
    """执行 start 子命令：启动服务并保持前台运行"""
    db_path = Path(args.db)
    logger.info("正在启动触发器服务，数据库: %s", db_path)

    service, conn = _create_service(db_path)
    service.start()
    logger.info("触发器服务已启动，按 Ctrl+C 停止")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止服务...")
    finally:
        service.stop()
        conn.close()
        logger.info("触发器服务已停止")


def run_status(args):
    """执行 status 子命令：显示服务心跳"""
    db_path = Path(args.db)
    service, conn = _create_service(db_path)
    try:
        print(service.heartbeat())
    finally:
        conn.close()


def run_list(args):
    """执行 list 子命令：打印详细触发器及回调信息"""
    db_path = Path(args.db)
    service, conn = _create_service(db_path)
    try:
        print(str(service))
    finally:
        conn.close()


def run_update(args):
    """执行 update 子命令：重新加载触发器并显示更新结果"""
    db_path = Path(args.db)
    service, conn = _create_service(db_path)
    try:
        service.update_triggers()
        print("触发器已重新加载，当前状态：")
        print(str(service))
    finally:
        conn.close()
