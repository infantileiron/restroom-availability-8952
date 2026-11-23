from fastapi import APIRouter, Depends

from src.controllers.identity import current_user
from src.schemas.identity import Login
from src.services.identity import sign_in

router = APIRouter(tags=['identity'])


@router.post('/login')
def login(payload: Login):
    return sign_in(payload)


@router.get('/me')
def me(user=Depends(current_user)):
    return user
