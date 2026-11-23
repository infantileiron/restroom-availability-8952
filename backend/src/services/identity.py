from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from src.config.runtime import JWT_SECRET
from src.models.database import connect
from src.utils.identity import matches


def sign_in(payload):
    with connect() as db:
        user = db.execute('SELECT * FROM users WHERE username = %s', (payload.username,)).fetchone()
    if not user or not matches(payload.password, user['password_hash']):
        raise HTTPException(401, '账号或密码不正确')
    del user['password_hash']
    expires = datetime.now(timezone.utc) + timedelta(hours=8)
    return {'user': user, 'token': jwt.encode({'sub': user['username'], 'exp': expires}, JWT_SECRET, algorithm='HS256')}
