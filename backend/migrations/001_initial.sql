CREATE TABLE IF NOT EXISTS users (
    username text PRIMARY KEY,
    display_name text NOT NULL,
    role text NOT NULL CHECK (role IN ('analyst', 'reviewer', 'viewer')),
    password_hash text NOT NULL
);
CREATE TABLE IF NOT EXISTS facilities (
    code text PRIMARY KEY,
    name text NOT NULL,
    district text NOT NULL
);
CREATE TABLE IF NOT EXISTS opening_windows (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    facility_code text NOT NULL REFERENCES facilities(code),
    weekday smallint NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    start_min smallint NOT NULL CHECK (start_min BETWEEN 0 AND 1439),
    end_min smallint NOT NULL CHECK (end_min BETWEEN 1 AND 2879),
    CHECK (end_min > start_min AND end_min - start_min <= 1440),
    UNIQUE (facility_code, weekday, start_min, end_min)
);
CREATE TABLE IF NOT EXISTS outages (
    code text PRIMARY KEY,
    facility_code text NOT NULL REFERENCES facilities(code),
    reason text NOT NULL CHECK (reason IN ('water', 'fault')),
    starts_at timestamp NOT NULL,
    ends_at timestamp NOT NULL,
    note text NOT NULL,
    CHECK (ends_at > starts_at)
);
CREATE INDEX IF NOT EXISTS outages_period ON outages (starts_at, ends_at);
CREATE TABLE IF NOT EXISTS snapshots (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    month char(7) NOT NULL,
    label text NOT NULL,
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'queued', 'ready', 'published', 'failed')),
    inputs jsonb NOT NULL,
    checksum char(64) NOT NULL,
    result jsonb,
    error text,
    created_by text NOT NULL REFERENCES users(username),
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    published_by text REFERENCES users(username),
    published_at timestamptz,
    UNIQUE (month, label)
);
CREATE TABLE IF NOT EXISTS audit_log (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor text NOT NULL,
    action text NOT NULL,
    subject text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
