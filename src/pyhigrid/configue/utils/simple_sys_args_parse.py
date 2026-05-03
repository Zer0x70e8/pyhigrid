#!/usr/bin/env python3
"""根据默认配置表 (TABLE) 和类型映射 (TYPE_MAP) 自动生成命令行参数解析器，
并解析出用户显式指定的覆盖项（优先级高于环境变量和默认值）。
"""

import argparse
from pathlib import Path
from typing import Sequence, Annotated, get_args, get_origin

from ..required_conf_table import TABLE, TYPE_MAP, UI

__all__ = ["create_parser", "parse_args_to_config", "deep_merge"]

TWO_NUM_TYPE = Annotated[Sequence[int], "length=2"]


def _deep_set(d: dict, keys: list, value) -> None:
    """在嵌套字典中设置值，自动创建中间字典。"""
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


def _flatten_config(config_, type_map, prefix=""):
    """
    递归遍历配置字典与类型字典，生成 (cli_flag, default, type_, help_str, path) 元组。
    path 为键的列表（如 ['log', 'verbose']），用于后续按路径重建嵌套字典。
    """
    entries = []

    def walk(c, tm, pre, current_path):
        for key, value in c.items():
            full_key = f"{pre}.{key}" if pre else key
            cli_flag = "--" + full_key.replace(".", "-").replace("_", "-")
            path = current_path + [key]

            # 判断是否应继续递归：值为 dict 且 (类型映射缺失该键，或映射指向 dict)
            if (
                    isinstance(value, dict)
                    and (
                    key not in tm
                    or isinstance(tm.get(key), dict)
            )
            ):
                # 递归进入嵌套配置（包括 env_override、app 等未在 TYPE_MAP 中定义的子字典）
                walk(value, tm.get(key, {}), full_key, path)
            else:
                # 叶子节点
                typ = tm.get(key)
                if typ is None:
                    typ = type(value) if value is not None else str

                # 处理带有标注的类型（如 TWO_NUM_TYPE）
                origin = get_origin(typ)
                if origin is Annotated:
                    typ = get_args(typ)[0]  # 提取基础类型

                help_str = f"默认值: {value}"
                entries.append((cli_flag, value, typ, help_str, path))

    walk(config_, type_map, prefix, [])
    return entries


def _parse_two_int(arg: str):
    """解析 '800,600' 格式的字符串为包含两个整数的元组。"""
    parts = arg.split(",")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"需要两个整数，用逗号分隔，例如 800,600，实际收到: {arg!r}"
        )
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(f"无法将 {arg!r} 转换为两个整数")


def _build_type_converter(typ):
    """
    根据 typ 返回 argparse 的 type= 参数。
    - Path -> Path
    - UI -> UI（直接使用枚举构造器）
    - Sequence[int] (TWO_NUM_TYPE) -> _parse_two_int
    - 其他 -> typ
    """
    if typ == Path:
        return Path
    if typ == UI:
        return UI
    origin = get_origin(typ)
    if origin is Sequence or origin is list:
        args = get_args(typ)
        if args == (int,) or args == (int,):
            return _parse_two_int
    return typ


def _bool_flag_args(cli_flag, dest, default, help_str):
    """
    返回用于 argparse 的布尔参数配置。
    使用 store_const 且不设默认值（default=SUPPRESS），
    这样只有用户显式传入时才会出现在结果中。
    """
    if default:
        # 默认 True，提供 --no-xxx 将其设为 False
        no_flag = "--no-" + cli_flag[2:]
        return [
            (cli_flag, dict(action="store_const", const=True, dest=dest, help=help_str + " (显式开启)")),
            (no_flag, dict(action="store_const", const=False, dest=dest, help=help_str + " (关闭)")),
        ]
    else:
        # 默认 False，提供 --xxx 将其设为 True
        return [
            (cli_flag, dict(action="store_const", const=True, dest=dest, help=help_str + " (开启)")),
        ]


# 需要手动处理的顶层键
MANUAL_KEYS = {"m", "O"}

def create_parser(description="PyHiGrid 命令行参数"):
    parser = argparse.ArgumentParser(description=description)

    # 自动生成除 m 和 O 以外的所有参数
    entries = _flatten_config(TABLE, TYPE_MAP)

    for cli_flag, default, typ, help_str, path in entries:
        # 跳过手动处理的键
        if len(path) == 1 and path[0] in MANUAL_KEYS:
            continue

        dest = "__".join(path)
        if typ == bool or typ is bool:
            for flag, kwargs in _bool_flag_args(cli_flag, dest, default, help_str):
                parser.add_argument(flag, **kwargs)
        else:
            convert = _build_type_converter(typ)
            parser.add_argument(
                cli_flag,
                type=convert,
                dest=dest,
                default=argparse.SUPPRESS,
                help=help_str,
            )

    # --- 手动添加 Python 解释器风格参数 ---
    # -m MODULE
    parser.add_argument(
        "-m", "--m",
        dest="m",
        nargs="?",  # 参数可选
        const="__default__",  # 不带参数时的默认值
        type=str,
        default=argparse.SUPPRESS,
        help="run library module as a script (optional module name)"
    )
    # -O : 基本优化
    parser.add_argument(
        "-O",
        dest="O",
        action="store_const",
        const=1,
        default=argparse.SUPPRESS,
        help="enable basic optimizations"
    )
    # -OO : 更强优化（无值参数，直接出现即激活）
    parser.add_argument(
        "-OO",
        dest="O",
        action="store_const",
        const=2,
        default=argparse.SUPPRESS,
        help="discard docstrings in addition to -O optimizations"
    )

    # 原有的 --env-prefix 参数依然保留
    parser.add_argument(
        "--env-prefix",
        dest="env_override__prefix",
        default=argparse.SUPPRESS,
        help="覆盖环境变量前缀（默认从配置读取）",
    )

    return parser


def parse_args_to_config(args=None):
    """
    解析命令行参数，返回用户显式提供的覆盖字典（嵌套结构与 TABLE 一致）。
    未在命令行指定的键不会出现在返回的字典中。
    """
    parser = create_parser()
    ns = parser.parse_args(args)

    result = {}
    for dest, value in vars(ns).items():
        # dest 形如 "log__verbose" 或 "env_override__prefix"
        keys = dest.split("__")
        _deep_set(result, keys, value)

    return result


def deep_merge(base: dict, override: dict):
    """将 override 中的内容递归合并到 base 中, override 优先级更高"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value


# 示例用法
if __name__ == "__main__":
    # 模拟命令行输入
    argv = [
        "prog",
        "--debug",
        "--log-verbose",
        "--ui-default-window-size", "1024,768",
        "--path-data", "/custom/data",
    ]
    # 仅打印显式覆盖项
    overrides = parse_args_to_config(argv)
    print("命令行覆盖项：")
    print(overrides)
