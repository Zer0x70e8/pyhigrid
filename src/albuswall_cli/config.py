#
"""cli config"""

import logging

DEFAULT_DB = "test_media.db"

# 排序字段映射（供 view 命令使用）
SORT_MAP = {
    "taken_at": "taken_at",
    "added_at": "added_at",
    "sort_order": "sort_order",
}


def setup_logging(verbose: bool):
    """配置日志级别和格式"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=level,
    )
    # 减少第三方库的日志噪音
    logging.getLogger("PIL").setLevel(logging.WARNING)
