from psycopg.types.json import Jsonb

VERSION_SUMMARY = '''id, label, status, adjudication_mode, checksum, adjudication,
                     created_by, created_at, activated_by, activated_at'''

WINDOW_COLUMNS = '''id, version_id, facility_code, window_type, source, open_date,
                    start_min, end_min, note, created_by, created_at'''


def create_version(db, label, mode, actor):
    return db.execute('''INSERT INTO rule_versions (label, adjudication_mode, created_by)
                         VALUES (%s, %s, %s) RETURNING id, label, status, adjudication_mode,
                         created_by, created_at''', (label, mode, actor)).fetchone()


def get_version(db, version_id, for_update=False):
    lock = ' FOR UPDATE' if for_update else ''
    return db.execute(f'SELECT {VERSION_SUMMARY} FROM rule_versions WHERE id = %s' + lock,
                      (version_id,)).fetchone()


def list_versions(db):
    return db.execute(f'''SELECT {VERSION_SUMMARY},
                          (SELECT count(*) FROM temp_windows w WHERE w.version_id = v.id) AS window_count
                          FROM rule_versions v ORDER BY id DESC''').fetchall()


def active_version(db, for_update=False):
    lock = ' FOR UPDATE' if for_update else ''
    return db.execute(f"SELECT {VERSION_SUMMARY} FROM rule_versions"
                      f" WHERE status = 'active'" + lock).fetchone()


def list_windows(db, version_id):
    return db.execute(f'''SELECT {WINDOW_COLUMNS} FROM temp_windows
                          WHERE version_id = %s ORDER BY facility_code, open_date, id''',
                      (version_id,)).fetchall()


def insert_window(db, payload, version_id, actor):
    # ON CONFLICT DO NOTHING 完成版本内归一化：完全相同的窗口重复录入不产生新行。
    return db.execute('''INSERT INTO temp_windows
                         (version_id, facility_code, window_type, source, open_date,
                          start_min, end_min, note, created_by)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                         ON CONFLICT DO NOTHING RETURNING id''',
                      (version_id, payload.facility_code, payload.window_type, payload.source,
                       payload.open_date, payload.start_min, payload.end_min,
                       payload.note, actor)).fetchone()


def find_window(db, window_id, version_id):
    return db.execute('''SELECT id, version_id FROM temp_windows
                         WHERE id = %s AND version_id = %s FOR UPDATE''',
                      (window_id, version_id)).fetchone()


def delete_window(db, window_id):
    return db.execute('DELETE FROM temp_windows WHERE id = %s', (window_id,)).rowcount


def activate(db, version_id, actor, adjudication, checksum):
    """原子激活：旧 active 落回草稿，新版本生效。失败时调用方整体回滚，旧版保留。"""
    db.execute("UPDATE rule_versions SET status = 'draft' WHERE status = 'active'")
    return db.execute('''UPDATE rule_versions SET status = 'active', adjudication = %s,
                         checksum = %s, activated_by = %s, activated_at = now()
                         WHERE id = %s RETURNING id''',
                      (Jsonb(adjudication), checksum, actor, version_id)).fetchone()
