#
""""""

import glob
import shutil
from pathlib import Path
from typing import Iterable


def get_resource(
        work_dir: Path | str,
        pattern: str,
        filenames: Iterable[str],
        ignore_extension: bool = False
):
    """
    :param work_dir:  需要处理的目标根目录
    :param pattern:  glob pattern
    :param filenames:  目标文件列表
    :param ignore_extension:  是否忽略尾缀
    """
    work_dir = Path(work_dir)
    if ignore_extension:
        target_names = {
            Path(i).stem for i in filenames
        }
    else:
        target_names = set(filenames)
    full_pattern = str(work_dir / pattern)
    matched_files = []

    for path in glob.iglob(full_pattern, recursive=True):
        path = Path(path)
        if path.is_file():
            compare_name = path.stem if ignore_extension else path.name
            if compare_name in target_names:
                matched_files.append(path)
    return matched_files


def ensure_directory_from_template(
        target_dir: Path | str,
        template: Path | str,
        template_is_name: bool = False,
) -> bool:
    """:return is create template."""
    target_dir = Path(target_dir)
    if not target_dir.parent.is_dir():
        e = f"Directory not found: {target_dir.parent}"
        raise RuntimeError(e)
    if target_dir.is_dir():
        return False
    else:
        if template_is_name:
            (target_dir / template).mkdir()
        else:
            shutil.copytree(template, target_dir, dirs_exist_ok=True)
        return True
