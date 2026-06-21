# constants
""""""

import uuid

# size
THUMB_SIZE_SMALL = 128
THUMB_SIZE_MEDIUM = 256
THUMB_SIZE_LARGE = 512

# 支持的文件扩展名
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.tif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# album UUID
VIRTUAL_ALBUM_NAMESPACE  = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # 固定的命名空间

UUID_ALL_PHOTOS = uuid.uuid5(VIRTUAL_ALBUM_NAMESPACE, 'all_photos')
UUID_UNORGANIZED = uuid.uuid5(VIRTUAL_ALBUM_NAMESPACE, 'unorganized')
UUID_FAVORITES = uuid.uuid5(VIRTUAL_ALBUM_NAMESPACE, 'favorites')
UUID_RECENTLY_DELETED = uuid.uuid5(VIRTUAL_ALBUM_NAMESPACE, 'recently_deleted')
UUID_VIDEOS = uuid.uuid5(VIRTUAL_ALBUM_NAMESPACE, 'videos')
