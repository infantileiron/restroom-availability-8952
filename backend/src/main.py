import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from redis.exceptions import RedisError

from scripts.seed_demo import seed
from src.config.runtime import REDIS, SEED_DEMO
from src.middlewares.http import install
from src.models.database import connect, migrate
from src.routes import calendar, identity, snapshots


@asynccontextmanager
async def lifecycle(app):
    migrate()
    if SEED_DEMO:
        try:
            seed()
        except Exception:
            logging.getLogger(__name__).exception('Demo seed failed')
    yield


app = FastAPI(title='坊洁巡维', lifespan=lifecycle)
install(app)
app.include_router(identity.router)
app.include_router(calendar.router)
app.include_router(snapshots.router)


@app.get('/health')
def health():
    with connect() as db:
        db.execute('SELECT 1 FROM snapshots LIMIT 1')
    try:
        REDIS.ping()
    except RedisError:
        raise HTTPException(503, 'Redis 暂不可用') from None
    return {'status': 'ok'}
