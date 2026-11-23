import hashlib
import json
import logging

from fastapi import HTTPException
from psycopg.types.json import Jsonb
from redis.exceptions import RedisError

from src.config.runtime import REDIS, WAKE_QUEUE
from src.constants.business import Role, Status
from src.models import calendar
from src.models.audit import audit
from src.models.database import connect
from src.models.snapshots import SUMMARY, find, listing
from src.utils.calendar import month_bounds

logger = logging.getLogger(__name__)


def capture(payload, actor):
    with connect() as db:
        db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        events = calendar.outages(db, month_bounds(payload.month))
        for event in events:
            for field in ('starts_at', 'ends_at'):
                event[field] = event[field].isoformat(timespec='minutes')
        inputs = {'month': payload.month, 'facilities': calendar.facilities(db), 'outages': events}
        canonical = json.dumps(inputs, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
        digest = hashlib.sha256(canonical).hexdigest()
        inserted = db.execute(f'''INSERT INTO snapshots (month, label, inputs, checksum, created_by)
                                  VALUES (%s, %s, %s, %s, %s) RETURNING {SUMMARY}''',
                              (payload.month, payload.label, Jsonb(inputs), digest, actor)).fetchone()
        audit(db, actor, 'snapshot.capture', inserted['id'])
        return inserted


def list_visible(user):
    with connect() as db:
        return listing(db, user['role'] == Role.VIEWER)


def detail(snapshot_id, user):
    with connect() as db:
        snapshot = find(db, snapshot_id)
    if not snapshot or (user['role'] == Role.VIEWER and snapshot['status'] != Status.PUBLISHED):
        raise HTTPException(404, '在当前权限下找不到这份快照')
    return snapshot


def transition(snapshot_id, actor, action):
    with connect() as db:
        snapshot = find(db, snapshot_id, for_update=True)
        if not snapshot:
            raise HTTPException(404, '找不到这份快照')
        if action == 'run':
            if snapshot['status'] not in (Status.DRAFT, Status.FAILED):
                raise HTTPException(409, '仅待核算或失败版本可以执行')
            statement = "status = 'queued', error = NULL, finished_at = NULL"
            args = ()
        else:
            if snapshot['status'] != Status.READY:
                raise HTTPException(409, '请等待核算完成后再发布')
            statement = "status = 'published', published_by = %s, published_at = now()"
            args = (actor,)
        row = db.execute(f'UPDATE snapshots SET {statement} WHERE id = %s RETURNING {SUMMARY}',
                         (*args, snapshot_id)).fetchone()
        audit(db, actor, f'snapshot.{action}', snapshot_id)
    if action == 'run':
        try:
            REDIS.lpush(WAKE_QUEUE, str(snapshot_id))
        except RedisError:
            logger.warning('Redis wake-up failed; worker will poll the persistent queue')
    return row
