def facilities(db):
    sites = db.execute('SELECT * FROM facilities ORDER BY code').fetchall()
    indexed = {site['code']: dict(site, windows=[]) for site in sites}
    windows = db.execute('''SELECT facility_code, weekday, start_min, end_min FROM opening_windows
                            ORDER BY facility_code, weekday, start_min, end_min''')
    for window in windows:
        indexed[window.pop('facility_code')]['windows'].append(window)
    return list(indexed.values())


def outages(db, period=None):
    query = 'SELECT * FROM outages'
    params = ()
    if period:
        query += ' WHERE starts_at < %s AND ends_at > %s'
        params = (period[1], period[0])
    return db.execute(query + ' ORDER BY starts_at DESC, code', params).fetchall()
