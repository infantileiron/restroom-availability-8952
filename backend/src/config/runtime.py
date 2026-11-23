import os
from pathlib import Path

from redis import Redis

JWT_SECRET = os.environ.get('JWT_SECRET', 'local-restroom-demo-key-replace-before-deploy')
ARTIFACT_DIR = Path(os.environ.get('ARTIFACT_DIR', './artifacts'))
SEED_DEMO = os.environ.get('SEED_DEMO', 'true').lower() == 'true'
REDIS = Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'), socket_timeout=5)
WAKE_QUEUE = 'restrooms:worker:wake'
