#
""""""

from .core import get, CURRENT_PATH, FOLDER_ALIASES

__all__ = ["get", "CURRENT_PATH"] + list(FOLDER_ALIASES.keys())

def __getattr__(name):
    # 直接返回默认文件 Path
    if name in FOLDER_ALIASES:
        return get(name)
    # 支持以 `_dir` 结尾获取文件夹 Path
    if name.endswith("_dir"):
        alias = name[:-4]  # cut "_dir"
        if alias in FOLDER_ALIASES:
            return get(alias, as_folder=True)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# 可选：让 IDE 能列出可用属性
def __dir__():
    return sorted(globals().keys()) + list(FOLDER_ALIASES.keys()) + [f"{k}_dir" for k in FOLDER_ALIASES]
