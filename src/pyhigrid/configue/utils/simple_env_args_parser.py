#!/usr/bin/env python3
""""""

import os
import copy
from pathlib import Path
from typing import List, Tuple, Any, Generator

from ..required_conf_table import TABLE, TYPE_MAP, UI, TWO_NUM_TYPE

__all__ = ["parse_env_config", "update_config_from_env"]


def _parse_bool(value: str) -> bool:
    """将常见布尔字符串转换为布尔值"""
    v = value.strip().lower()
    if v in ("true", "1", "yes", "on"):
        return True
    if v in ("false", "0", "no", "off"):
        return False
    raise ValueError(f"无法解析为布尔值: '{value}'")


def _parse_two_num(value: str) -> Tuple[int, int]:
    """解析用逗号分隔的两个整数 (如 '800,600')"""
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 2:
        raise ValueError(f"需要两个整数，但得到: '{value}'")
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        raise ValueError(f"无法将 '{value}' 解析为两个整数")


def _convert_value(raw: str, target_type: type) -> Any:
    """将原始字符串按照目标类型进行转换"""
    if target_type == bool:
        return _parse_bool(raw)
    if target_type == int:
        return int(raw)
    if target_type == float:
        return float(raw)
    if target_type == str:
        return raw
    if target_type == Path:
        return Path(raw)
    if target_type == UI:
        # 先尝试按名称匹配，再尝试按值匹配
        try:
            return UI[raw]
        except KeyError:
            for member in UI:
                if member.value == raw:
                    return member
            raise ValueError(f"无效的 UI 值: '{raw}'")
    if target_type is TWO_NUM_TYPE:
        return _parse_two_num(raw)
    raise TypeError(f"不支持的环境变量类型: {target_type}")


def _deep_get(d: dict, keys: List[str], default=None):
    """获取嵌套字典中指定路径的值"""
    for key in keys:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            return default
    return d


def _deep_set(d: dict, keys: List[str], value):
    """在嵌套字典中设置指定路径的值，自动创建中间字典"""
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


def _iter_env_keys(prefix: str, type_map: dict, parent_keys: List[str] = None
                   ) -> Generator[Tuple[str, List[str]], None, None]:
    """
    遍历类型映射的所有叶子节点，生成 (环境变量名, 配置路径) 元组。
    环境变量名规则: <前缀>_<各层键大写以下划线连接>
    例如 prefix='PYHIGRID_'，路径 ['log','verbose'] -> 'PYHIGRID_LOG_VERBOSE'
    """
    if parent_keys is None:
        parent_keys = []
    for key, subtype in type_map.items():
        if isinstance(subtype, dict):
            yield from _iter_env_keys(prefix, subtype, parent_keys + [key])
        else:
            var_name = prefix + "_".join(parent_keys + [key]).upper()
            yield var_name, parent_keys + [key]


def parse_env_config(base_config: dict = None,
                     type_map: dict = None,
                     prefix: str = None) -> dict:
    """
    根据 TYPE_MAP 读取环境变量，生成覆盖后的配置字典。

    :param base_config: 基础配置字典，默认使用 required_conf_table.TABLE
    :param type_map:    类型映射字典，默认使用 required_conf_table.TYPE_MAP
    :param prefix:      环境变量前缀，
                        默认从 base_config['env_override']['prefix'] 获取，
                        若不存在则回退为 'PYHIGRID_'
    :return:            深拷贝并完成覆盖的新配置字典
    """
    if base_config is None:
        base_config = TABLE
    if type_map is None:
        type_map = TYPE_MAP

    # 允许 base_config 自身指定前缀
    env_override = base_config.get("env_override", {})
    if prefix is None:
        prefix = env_override.get("prefix", "PYHIGRID_")

    config_ = copy.deepcopy(base_config)

    for env_var, keys in _iter_env_keys(prefix, type_map):
        raw_value = os.environ.get(env_var)
        if raw_value is None:
            continue

        target_type = _deep_get(type_map, keys)
        try:
            value = _convert_value(raw_value, target_type)
        except Exception as e:
            raise ValueError(f"解析环境变量 {env_var} 失败: {e}") from e

        _deep_set(config_, keys, value)

    return config_


def update_config_from_env(target_dict: dict = None) -> dict:
    """
    直接更新传入的配置字典（就地修改），并返回该字典。
    若未提供 target_dict，则更新模块级 TABLE 并返回（谨慎使用）。
    """
    new_conf = parse_env_config(target_dict)
    if target_dict is not None:
        target_dict.clear()
        target_dict.update(new_conf)
        return target_dict
    else:
        TABLE.clear()
        TABLE.update(new_conf)
        return TABLE


if __name__ == "__main__":
    # 从环境变量读取并生成最终配置（不修改原始 TABLE）
    config = parse_env_config()
    debug_mode = config["debug"]
    ui_size = config["ui"]["default_window_size"]  # 已转为 (800, 600) 这样的元组
