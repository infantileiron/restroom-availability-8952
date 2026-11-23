-- 节庆临时窗口：规则版本 + 临时窗口记录
-- 规则记录按版本归一化；已激活（active）版本不可变，激活失败保留当前旧版。
CREATE TABLE IF NOT EXISTS rule_versions (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    label text NOT NULL,
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active')),
    adjudication_mode text NOT NULL DEFAULT 'priority'
        CHECK (adjudication_mode IN ('priority', 'minute')),
    adjudication jsonb,
    checksum char(64),
    created_by text NOT NULL REFERENCES users(username),
    created_at timestamptz NOT NULL DEFAULT now(),
    activated_by text REFERENCES users(username),
    activated_at timestamptz
);
-- 同一时刻至多一个生效版本；草稿允许多个并存。
CREATE UNIQUE INDEX IF NOT EXISTS rule_versions_one_active
    ON rule_versions ((status = 'active')) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS temp_windows (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version_id bigint NOT NULL REFERENCES rule_versions(id),
    facility_code text NOT NULL REFERENCES facilities(code),
    window_type text NOT NULL CHECK (window_type IN ('extension', 'reduction', 'closed')),
    source text NOT NULL CHECK (source IN ('festival', 'station', 'hotline')),
    open_date date NOT NULL,
    start_min smallint NOT NULL CHECK (start_min BETWEEN 0 AND 1439),
    end_min smallint NOT NULL CHECK (end_min BETWEEN 1 AND 2879),
    note text NOT NULL DEFAULT '',
    created_by text NOT NULL REFERENCES users(username),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (end_min > start_min AND end_min - start_min <= 1440),
    -- 归一化去重：同一版本内完全相同的窗口只保留一条
    UNIQUE (version_id, facility_code, window_type, source, open_date, start_min, end_min)
);
CREATE INDEX IF NOT EXISTS temp_windows_version ON temp_windows (version_id);
CREATE INDEX IF NOT EXISTS temp_windows_facility_date ON temp_windows (facility_code, open_date);
