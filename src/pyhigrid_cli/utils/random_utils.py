#
""""""

import string
import uuid
import random
from datetime import timedelta, datetime

from pyhigrid.domain.entities import FileImportInfo


def generate_random_fileinfo() -> FileImportInfo:
    """生成随机 FileImportInfo 用于测试导入"""
    uid = str(uuid.uuid4())
    name = "".join(random.choices(string.ascii_lowercase, k=8)) + ".jpg"
    path = f"/mock/import/{name}"
    mime = "image/jpeg"
    file_hash = "".join(random.choices("0123456789abcdef", k=64))
    size = random.randint(1000, 5000000)
    w, h = random.randint(800, 4000), random.randint(600, 3000)
    taken = (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat()
    return FileImportInfo(
        uuid=uid,
        file_path=path,
        original_name=name,
        mime_type=mime,
        file_hash=file_hash,
        file_size=size,
        width=w,
        height=h,
        taken_at=taken,
        thumb_path=f"/thumb/{name}",
        thumb_small_path=f"/thumb_small/{name}",
        thumb_medium_path=f"/thumb_medium/{name}",
    )
