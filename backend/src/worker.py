import logging
import time
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb
from redis.exceptions import RedisError

from src.config.runtime import REDIS, WAKE_QUEUE
from src.models.audit import audit
from src.models.database import connect
from src.services.availability import calculate
from src.services.exports import write_export

HEARTBEAT = Path('/tmp/heartbeat')
log = logging.getLogger(__name__)


def work_once():
    with connect() as db:
        job = db.execute("""SELECT id, inputs, checksum FROM snapshots WHERE status = 'queued'
                            ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED""").fetchone()
        if job is None:
            return False
        try:
            result = calculate(job['inputs'])
            write_export(job['id'], job['inputs'], job['checksum'], result)
        except Exception:
            log.exception('Snapshot %s failed', job['id'])
            db.execute("""UPDATE snapshots SET status = 'failed', error = %s, finished_at = now() WHERE id = %s""",
                       ('核算或导出失败，可重试当前版本', job['id']))
            audit(db, 'worker', 'snapshot.fail', job['id'])
        else:
            db.execute("UPDATE snapshots SET status = 'ready', result = %s, finished_at = now() WHERE id = %s",
                       (Jsonb(result), job['id']))
            audit(db, 'worker', 'snapshot.finish', job['id'])
    return True


def main():
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            worked = work_once()
        except psycopg.Error:
            log.warning('Waiting for the database and schema')
            time.sleep(2)
            continue
        HEARTBEAT.touch()
        if not worked:
            try:
                REDIS.blpop(WAKE_QUEUE, timeout=2)
            except RedisError:
                time.sleep(2)


if __name__ == '__main__':
    main()
