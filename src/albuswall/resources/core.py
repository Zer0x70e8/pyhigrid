#
""""""

from pathlib import Path

CURRENT_PATH = Path(__file__).parent

# ========== 映射表（请按需修改） ==========
# 1. 逻辑别名 -> 实际文件夹名（相对于 CURRENT_PATH）
FOLDER_ALIASES = {
    "theme": "default_theme_qss",
    "ico": "icon",
    "sql": "sql",
    # 可以添加更多别名，例如：
    # "style": "default_theme_qss",
}

# 2. 实际文件夹名 -> 该文件夹下的默认文件名（相对于实际文件夹）
DEFAULT_FILES = {
    "default_theme_qss": "main_window.qss",
    "icon": "image_icon.png",      # 可根据需要改为其他图标
    "sql": "media_library_schema.sql",
    # 如果某个文件夹没有默认文件，可以不加入此表，调用时若未指定 as_folder=True 则会报错
}
# ============================================

def get(alias: str, as_folder: bool = False) -> Path:
    """
    根据逻辑别名获取资源路径。

    Args:
        alias: 逻辑别名（必须在 FOLDER_ALIASES 中定义）。
        as_folder: 若为 True，返回实际文件夹路径；否则返回该文件夹下的默认文件路径。

    Returns:
        Path 对象，指向 CURRENT_PATH 内的文件或文件夹。

    Raises:
        KeyError: 如果 alias 未在 FOLDER_ALIASES 中定义，
                  或未指定默认文件且 as_folder=False。
        FileNotFoundError: 如果目标路径不存在或类型不匹配。
        ValueError: 如果解析后的路径越出了 CURRENT_PATH（路径穿越）。
    """
    # 解析逻辑别名到实际文件夹名
    if alias not in FOLDER_ALIASES:
        raise KeyError(f"Unknown alias: {alias}")
    actual_folder_name = FOLDER_ALIASES[alias]

    # 构建文件夹路径并检查安全性
    folder_path = (CURRENT_PATH / actual_folder_name).resolve()
    current_resolved = CURRENT_PATH.resolve()
    if not folder_path.is_relative_to(current_resolved):
        raise ValueError("Path traversal detected for folder")

    # 如果需要文件夹，直接返回
    if as_folder:
        if not folder_path.is_dir():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        return folder_path

    # 获取默认文件名（键为实际文件夹名）
    default_file = DEFAULT_FILES.get(actual_folder_name)
    if default_file is None:
        raise KeyError(f"No default file defined for folder '{actual_folder_name}'")

    # 构建文件路径并检查安全性
    file_path = (folder_path / default_file).resolve()
    if not file_path.is_relative_to(folder_path):
        raise ValueError("Path traversal detected for file")

    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    return file_path


if __name__ == "__main__":
    # 简单测试
    print("资源根目录:", CURRENT_PATH)
    print("默认主题文件:", get("theme"))
    print("图标文件夹:", get("icons", as_folder=True))
    print("SQL 文件:", get("sql"))