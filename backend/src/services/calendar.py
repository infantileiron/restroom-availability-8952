from fastapi import HTTPException

from src.models.audit import audit
from src.models.database import connect


def create_facility(payload, user):
    with connect() as db:
        row = db.execute('INSERT INTO facilities (code, name, district) VALUES (%s, %s, %s) RETURNING *',
                         (payload.code, payload.name, payload.district)).fetchone()
        audit(db, user, 'facility.create', payload.code)
        return row


def save_windows(code, payload, user):
    with connect() as db:
        if not db.execute('SELECT 1 FROM facilities WHERE code = %s FOR UPDATE', (code,)).fetchone():
            raise HTTPException(404, '设施不存在')
        added = []
        for day in sorted(payload.weekdays):
            row = db.execute('''INSERT INTO opening_windows (facility_code, weekday, start_min, end_min)
                                VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING
                                RETURNING weekday, start_min, end_min''',
                             (code, day, payload.start_min, payload.end_min)).fetchone()
            if row:
                added.append(row)
        if added:
            audit(db, user, 'opening.add', code)
        return {'added': added}


def create_outage(payload, user):
    with connect() as db:
        if not db.execute('SELECT 1 FROM facilities WHERE code = %s', (payload.facility_code,)).fetchone():
            raise HTTPException(404, '设施不存在')
        row = db.execute('''INSERT INTO outages (code, facility_code, reason, starts_at, ends_at, note)
                            VALUES (%(code)s, %(facility_code)s, %(reason)s, %(starts_at)s, %(ends_at)s, %(note)s)
                            RETURNING *''', payload.model_dump(mode='json')).fetchone()
        audit(db, user, 'outage.create', payload.code)
        return row
