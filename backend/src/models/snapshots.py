SUMMARY = '''id, month, label, status, checksum, error, created_by, created_at,
             finished_at, published_by, published_at'''


def listing(db, published_only):
    visibility = " WHERE status = 'published'" if published_only else ''
    return db.execute(f'SELECT {SUMMARY}, result->\'totals\' AS totals FROM snapshots'
                      + visibility + ' ORDER BY id DESC').fetchall()


def find(db, snapshot_id, for_update=False):
    lock = ' FOR UPDATE' if for_update else ''
    return db.execute(f'SELECT {SUMMARY}, result FROM snapshots WHERE id = %s' + lock,
                      (snapshot_id,)).fetchone()
