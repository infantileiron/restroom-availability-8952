import json

from src.models.database import connect
from src.utils.identity import hash_password

USERS = [('analyst', '林清', 'analyst'), ('reviewer', '陈亭', 'reviewer'), ('viewer', '周桐', 'viewer')]
SITES = [('FJ-01', '桥西便民公厕', '桥西片区'), ('FJ-02', '站前夜间公厕', '站前片区'),
         ('FJ-03', '河畔绿道公厕', '河畔片区'), ('FJ-04', '北坊整修公厕', '北坊片区')]
RULES = [('FJ-01', 0, 1440), ('FJ-02', 1200, 1560), ('FJ-02', 1290, 1380), ('FJ-03', 420, 1140)]
OUTAGES = [
    ('WX-1101', 'FJ-02', 'fault', '2026-10-31 23:20', '2026-11-01 00:30', '门锁复位，跨月交班'),
    ('WX-1102', 'FJ-01', 'water', '2026-11-12 06:10', '2026-11-12 07:00', '管线检修停水'),
    ('WX-1103', 'FJ-01', 'fault', '2026-11-12 06:40', '2026-11-12 07:25', '冲洗阀故障，和停水交叠'),
    ('WX-1104', 'FJ-02', 'water', '2026-11-12 23:30', '2026-11-13 00:45', '夜班支线停水'),
    ('WX-1105', 'FJ-02', 'fault', '2026-11-13 00:15', '2026-11-13 03:10', '设备恢复时间晚于闭馆'),
    ('WX-1106', 'FJ-03', 'fault', '2026-11-12 05:45', '2026-11-12 06:25', '晨巡故障，开放前已恢复'),
    ('WX-1107', 'FJ-03', 'water', '2026-11-12 18:30', '2026-11-12 19:30', '晚班停水跨过闭馆线'),
    ('WX-1108', 'FJ-04', 'fault', '2026-11-12 08:00', '2026-11-12 09:10', '整修期测试发现照明故障'),
]

# 节庆临时窗口演示：同一设施同日同时出现延长、缩短、整日关闭；含跨夜与来源冲突。
# (facility, type, source, open_date, start_min, end_min, note)
FESTIVAL_VERSION = ('十一月节庆窗口·首次发布', 'priority')
FESTIVAL_WINDOWS = [
    # 站前公厕：灯会延长至次日 03:00，跨夜按 11-14 开门日归属
    ('FJ-02', 'extension', 'festival', '2026-11-14', 1200, 1620, '灯会保障延长开放，跨夜至次日 03:00'),
    # 站前公厕同日：热线登记的缩短与节庆办延长在 20:00–22:00 冲突，优先级整体裁决
    ('FJ-02', 'reduction', 'hotline', '2026-11-14', 1200, 1320, '热线反映临时缩短，待裁决'),
    # 河畔公厕：节庆当日整日关闭
    ('FJ-03', 'closed', 'festival', '2026-11-14', 0, 1440, '河畔活动整日关闭'),
    # 桥西公厕：缩短与延长并存且不重叠
    ('FJ-01', 'reduction', 'station', '2026-11-14', 0, 360, '凌晨保障缩短'),
    ('FJ-01', 'extension', 'station', '2026-11-14', 1320, 1500, '晚间延长开放'),
]


def seed():
    with connect() as db, db.cursor() as cursor:
        cursor.executemany('INSERT INTO users VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING',
                           [(*user, hash_password('Fangjie2026!')) for user in USERS])
        cursor.executemany('INSERT INTO facilities VALUES (%s, %s, %s) ON CONFLICT DO NOTHING', SITES)
        cursor.executemany('''INSERT INTO opening_windows (facility_code, weekday, start_min, end_min)
                              VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING''',
                           [(code, day, start, end) for code, start, end in RULES for day in range(7)])
        cursor.executemany('INSERT INTO outages VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING', OUTAGES)
        festival = _seed_festival(db)
        keys = {
            'facilities': sorted(site[0] for site in SITES),
            'outages': sorted(row[0] for row in OUTAGES),
            'opening_windows': len(RULES) * 7,
            'rule_versions': festival,
            'users': sorted(user[0] for user in USERS),
        }
    return keys


def _seed_festival(db):
    existing = db.execute("SELECT id FROM rule_versions WHERE status = 'active'").fetchone()
    if existing:
        return {'active_version_id': existing['id'], 'window_count':
                db.execute('SELECT count(*) AS n FROM temp_windows WHERE version_id = %s',
                           (existing['id'],)).fetchone()['n']}
    from src.services.adjudication import adjudicate
    from psycopg.types.json import Jsonb
    import hashlib
    import json
    version = db.execute('''INSERT INTO rule_versions (label, adjudication_mode, created_by,
                            status, activated_by, activated_at)
                            VALUES (%s, %s, %s, 'active', %s, now()) RETURNING id''',
                         (FESTIVAL_VERSION[0], FESTIVAL_VERSION[1], 'analyst', 'analyst')).fetchone()
    records = []
    for n, (facility, window_type, source, open_date, start_min, end_min, note) in enumerate(FESTIVAL_WINDOWS, start=1):
        db.execute('''INSERT INTO temp_windows
                      (version_id, facility_code, window_type, source, open_date,
                       start_min, end_min, note, created_by)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'analyst')''',
                   (version['id'], facility, window_type, source, open_date, start_min, end_min, note))
        records.append({'id': n, 'facility_code': facility, 'window_type': window_type,
                        'source': source, 'open_date': open_date, 'start_min': start_min,
                        'end_min': end_min, 'note': note})
    result = adjudicate(records, FESTIVAL_VERSION[1])
    checksum = hashlib.sha256(json.dumps(
        {'mode': result['mode'], 'records': records}, sort_keys=True,
        separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    db.execute('UPDATE rule_versions SET adjudication = %s, checksum = %s WHERE id = %s',
               (Jsonb(result), checksum, version['id']))
    return {'active_version_id': version['id'], 'window_count': len(records)}


if __name__ == '__main__':
    print(json.dumps(seed(), ensure_ascii=False, sort_keys=True))
