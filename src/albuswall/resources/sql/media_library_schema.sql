-- =============================================================================
-- pyhigrid 媒体库初始建表脚本
-- 创建表、索引、约束，保证数据完整性和查询性能
-- =============================================================================

-- 启用 WAL 模式（持久化，仅需执行一次；重复执行无害）
PRAGMA journal_mode = WAL;

-- -----------------------------------------------------------------------------
-- 1. 资产主表
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assets (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid             TEXT    NOT NULL UNIQUE,
    file_path        TEXT    NOT NULL,
    thumb_path       TEXT,
    thumb_small_path TEXT,
    thumb_medium_path TEXT,
    original_name    TEXT    NOT NULL,
    mime_type        TEXT    NOT NULL,
    file_hash        TEXT    NOT NULL,
    file_size        INTEGER NOT NULL DEFAULT 0,
    width            INTEGER NOT NULL DEFAULT 0,
    height           INTEGER NOT NULL DEFAULT 0,
    taken_at         TEXT,
    city             TEXT,
    exif_json        TEXT,
    is_favorite      INTEGER NOT NULL DEFAULT 0,
    is_deleted       INTEGER NOT NULL DEFAULT 0,
    deleted_at       TEXT,
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now')),
    modified_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now'))
);

-- -----------------------------------------------------------------------------
-- 2. 相簿表
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS albums (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid           TEXT    NOT NULL UNIQUE,
    title          TEXT    NOT NULL,
    album_type     INTEGER NOT NULL DEFAULT 0,
    cover_asset_id INTEGER,
    sort_order     INTEGER NOT NULL DEFAULT 0,
    is_deleted     INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now')),
    modified_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now')),
    FOREIGN KEY (cover_asset_id) REFERENCES assets(id) ON DELETE SET NULL
);

-- -----------------------------------------------------------------------------
-- 3. 相簿-资产关联表
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS album_assets (
    album_id      INTEGER NOT NULL,
    asset_id      INTEGER NOT NULL,
    asset_taken_at TEXT,
    added_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now')),
    sort_order    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (album_id, asset_id),
    FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

-- =============================================================================
-- 索引 —— 覆盖所有常用查询与排序，确保大数据量下的性能
-- =============================================================================

-- 活跃资产哈希唯一，防止重复导入
CREATE UNIQUE INDEX IF NOT EXISTS idx_assets_active_hash
    ON assets(file_hash) WHERE is_deleted = 0;

-- 常用布尔字段过滤
CREATE INDEX IF NOT EXISTS idx_assets_deleted  ON assets(is_deleted);
CREATE INDEX IF NOT EXISTS idx_assets_favorite ON assets(is_favorite);

-- 相簿 UUID 快速查找
CREATE INDEX IF NOT EXISTS idx_albums_uuid ON albums(uuid);

-- 专辑内资产关联查询
CREATE INDEX IF NOT EXISTS idx_album_assets_album ON album_assets(album_id, asset_id);

-- 相簿资产查询的各种排序
CREATE INDEX IF NOT EXISTS idx_album_assets_added ON album_assets(album_id, added_at);
CREATE INDEX IF NOT EXISTS idx_album_assets_sort  ON album_assets(album_id, sort_order, asset_id);
CREATE INDEX IF NOT EXISTS idx_album_assets_taken ON album_assets(album_id, asset_taken_at);
