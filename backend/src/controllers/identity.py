import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config.runtime import JWT_SECRET
from src.constants.business import Role
from src.models.database import connect

bearer = HTTPBearer(auto_error=False)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None:
        raise HTTPException(401, '请先登录')
    try:
        token = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=['HS256'], options={'require': ['exp', 'sub']})
    except jwt.InvalidTokenError:
        raise HTTPException(401, '登录已失效，请重新登录') from None
    with connect() as db:
        user = db.execute('SELECT username, role, display_name FROM users WHERE username = %s', (token['sub'],)).fetchone()
    if not user:
        raise HTTPException(401, '账号不可用')
    return user


def require(role: Role):
    def authorized(user=Depends(current_user)):
        if user['role'] != role:
            raise HTTPException(403, '当前角色无此操作权限')
        return user
    return authorized
