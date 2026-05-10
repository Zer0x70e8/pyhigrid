-- =============================================================================
-- pyhigrid 媒体库初始建表脚本
-- 创建表、索引、约束，保证数据完整性和查询性能
-- =============================================================================

-- 强制启用外键约束（需在每连接执行，这里作为提醒；database.py 已在连接时执行）
-- PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- 1. 资产主表
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assets (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid             TEXT    NOT NULL UNIQUE,                -- 全局唯一标识
    file_path        TEXT    NOT NULL,                       -- 文件系统路径
    thumb_path       TEXT,                                   -- 大缩略图路径
    thumb_small_path TEXT,                                   -- 小缩略图路径
    thumb_medium_path TEXT,                                  -- 中缩略图路径
    original_name    TEXT    NOT NULL,                       -- 原始文件名
    mime_type        TEXT    NOT NULL,                       -- MIME 类型
    file_hash        TEXT    NOT NULL,                       -- SHA-256 哈希
    file_size        INTEGER NOT NULL DEFAULT 0,             -- 文件大小（字节）
    width            INTEGER NOT NULL DEFAULT 0,             -- 图像宽度
    height           INTEGER NOT NULL DEFAULT 0,             -- 图像高度
    taken_at         TEXT,                                   -- 拍摄时间 (ISO 8601)
    city             TEXT,                                   -- 城市信息
    exif_json        TEXT,                                   -- EXIF 原始数据 (JSON 字符串)
    is_favorite      INTEGER NOT NULL DEFAULT 0,             -- 是否收藏 (0/1)
    is_deleted       INTEGER NOT NULL DEFAULT 0,             -- 软删除标记 (0/1)
    deleted_at       TEXT,                                   -- 删除时间
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now')),
    modified_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now'))
);

-- -----------------------------------------------------------------------------
-- 2. 相簿表
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS albums (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid           TEXT    NOT NULL UNIQUE,                  -- 相簿唯一标识
    title          TEXT    NOT NULL,                         -- 相簿标题
    album_type     INTEGER NOT NULL DEFAULT 0,               -- 0:手动 1:智能 3:收藏 4:最近删除 5:所有照片 6:视频 7:未整理
    cover_asset_id INTEGER,                                  -- 封面资产 ID
    sort_order     INTEGER NOT NULL DEFAULT 0,               -- 排序权重
    is_deleted     INTEGER NOT NULL DEFAULT 0,               -- 软删除
    created_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now')),
    modified_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now')),
    FOREIGN KEY (cover_asset_id) REFERENCES assets(id) ON DELETE SET NULL
);

-- -----------------------------------------------------------------------------
-- 3. 相簿-资产关联表
--    · 复合主键保证同一相簿不会重复添加同一资产
--    · 级联删除保证一致性
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS album_assets (
    album_id      INTEGER NOT NULL,
    asset_id      INTEGER NOT NULL,
    asset_taken_at TEXT,                                    -- 冗余拍摄时间，便于排序
    added_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now')),
    sort_order    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (album_id, asset_id),
    FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

-- =============================================================================
-- 索引 —— 覆盖所有常用查询与排序，确保大数据量下的性能
-- =============================================================================

-- 4. 活跃资产业务去重：同一个 file_hash 在系统中只能有一个 is_deleted=0 的记录
--    (需要 SQLite 3.8.0+；老版本会在 database.py 中自动回退为普通索引)
CREATE UNIQUE INDEX IF NOT EXISTS idx_assets_active_hash
    ON assets(file_hash) WHERE is_deleted = 0;

-- 5. 常用布尔字段过滤
CREATE INDEX IF NOT EXISTS idx_assets_deleted  ON assets(is_deleted);
CREATE INDEX IF NOT EXISTS idx_assets_favorite ON assets(is_favorite);

-- 6. 相簿 UUID 快速查找（导入时使用）
CREATE INDEX IF NOT EXISTS idx_albums_uuid ON albums(uuid);

-- 7. 相簿资产查询的各种排序方式
CREATE INDEX IF NOT EXISTS idx_album_assets_added ON album_assets(album_id, added_at);
CREATE INDEX IF NOT EXISTS idx_album_assets_sort  ON album_assets(album_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_album_assets_taken ON album_assets(album_id, asset_taken_at);
