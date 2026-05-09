-- ================================================================
-- 个人媒体库 MVP 版（最终强化・单用户・全相簿统一）
-- SQLite 3 可用
-- 时间格式：ISO 8601 (YYYY-MM-DDTHH:MM:SS.sss)
-- ================================================================
PRAGMA foreign_keys = ON;

-- ================================================================
-- 1. 资产表
-- ================================================================
CREATE TABLE assets (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid              TEXT    NOT NULL UNIQUE,

    file_path         TEXT    NOT NULL,
    thumb_path        TEXT    DEFAULT NULL,
    thumb_small_path  TEXT    DEFAULT NULL,
    thumb_medium_path TEXT    DEFAULT NULL,
    original_name     TEXT    DEFAULT NULL,
    mime_type         TEXT    NOT NULL DEFAULT 'image/jpeg',
    file_hash         TEXT    DEFAULT NULL,
    file_size         INTEGER NOT NULL DEFAULT 0,
    width             INTEGER NOT NULL,
    height            INTEGER NOT NULL,
    duration          REAL    DEFAULT 0.0,

    taken_at          TEXT    NOT NULL,          -- 应用层必须保证为 ISO8601 字符串

    city              TEXT    DEFAULT NULL,
    persons           TEXT    DEFAULT NULL,      -- MVP 阶段逗号分隔即可
    exif_json         TEXT    DEFAULT NULL,

    is_favorite       INTEGER NOT NULL DEFAULT 0 CHECK (is_favorite IN (0, 1)),
    is_deleted        INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    deleted_at        TEXT    DEFAULT NULL,

    added_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
    modified_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
);

-- 索引
CREATE INDEX idx_assets_order   ON assets (is_deleted, taken_at DESC, id DESC);
CREATE INDEX idx_assets_deleted ON assets (is_deleted, deleted_at);
CREATE INDEX idx_assets_hash    ON assets (file_hash);
CREATE INDEX idx_assets_city    ON assets (city, taken_at DESC);
CREATE INDEX idx_assets_fav     ON assets (is_favorite, is_deleted, taken_at DESC);
CREATE INDEX idx_assets_mime    ON assets (mime_type, is_deleted, taken_at DESC);

-- 自动更新 modified_at（应用层不显式修改时）
CREATE TRIGGER trg_assets_update AFTER UPDATE ON assets
WHEN old.modified_at = new.modified_at
BEGIN
    UPDATE assets SET modified_at = strftime('%Y-%m-%dT%H:%M:%f', 'now')
    WHERE id = new.id;
END;

-- 资产软删除时，自动从所有手动相簿移除
CREATE TRIGGER trg_assets_soft_delete AFTER UPDATE OF is_deleted ON assets
WHEN new.is_deleted = 1 AND old.is_deleted = 0
BEGIN
    DELETE FROM album_assets WHERE asset_id = new.id;
END;

-- 资产拍摄时间更新时，同步 album_assets 冗余字段
CREATE TRIGGER trg_assets_taken_at_update AFTER UPDATE OF taken_at ON assets
WHEN old.taken_at != new.taken_at
BEGIN
    UPDATE album_assets SET asset_taken_at = new.taken_at
    WHERE asset_id = new.id;
END;

-- ================================================================
-- 2. 相簿表（统一所有视图）
-- ================================================================
CREATE TABLE albums (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid            TEXT    NOT NULL UNIQUE,

    title           TEXT    NOT NULL,
    album_type      INTEGER NOT NULL DEFAULT 0
                    CHECK (album_type IN (0,1,3,4,5,6,7)),
    parent_id       INTEGER DEFAULT NULL REFERENCES albums(id) ON DELETE SET NULL,
    cover_asset_id  INTEGER DEFAULT NULL REFERENCES assets(id) ON DELETE SET NULL,

    sort_order      INTEGER NOT NULL DEFAULT 0,
    is_deleted      INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    deleted_at      TEXT    DEFAULT NULL,

    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
);

CREATE INDEX idx_albums_active ON albums (is_deleted);
CREATE INDEX idx_albums_parent ON albums (parent_id);

CREATE TRIGGER trg_albums_update AFTER UPDATE ON albums
WHEN old.updated_at = new.updated_at
BEGIN
    UPDATE albums SET updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now')
    WHERE id = new.id;
END;

-- ================================================================
-- 3. 智能相簿规则表
-- ================================================================
CREATE TABLE smart_album_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    album_id    INTEGER NOT NULL UNIQUE,
    rule_json   TEXT    NOT NULL,
    FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE
);

-- ================================================================
-- 4. 相簿-资产关联表（仅手动相簿使用）
-- ================================================================
CREATE TABLE album_assets (
    album_id        INTEGER NOT NULL,
    asset_id        INTEGER NOT NULL,

    asset_taken_at  TEXT    NOT NULL DEFAULT '1970-01-01T00:00:00',
    added_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
    sort_order      INTEGER NOT NULL DEFAULT 0,

    PRIMARY KEY (album_id, asset_id),
    FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id)  REFERENCES assets(id)  ON DELETE CASCADE
);

CREATE INDEX idx_album_sort  ON album_assets (album_id, sort_order, asset_id);
CREATE INDEX idx_album_taken ON album_assets (album_id, asset_taken_at, asset_id);
CREATE INDEX idx_album_added ON album_assets (album_id, added_at DESC, asset_id DESC);
CREATE INDEX idx_asset_album ON album_assets (asset_id);

-- ================================================================
-- 5. 内置相簿初始数据
-- ================================================================
INSERT OR IGNORE INTO albums (uuid, title, album_type, sort_order, is_deleted) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Favorites',        3, 1, 0),
    ('00000000-0000-0000-0000-000000000002', 'Recently Deleted', 4, 2, 0),
    ('00000000-0000-0000-0000-000000000003', 'All Photos',       5, 3, 0),
    ('00000000-0000-0000-0000-000000000004', 'Videos',           6, 4, 0),
    ('00000000-0000-0000-0000-000000000005', 'Unorganized',      7, 5, 0);
