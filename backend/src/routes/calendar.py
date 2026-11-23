from fastapi import APIRouter, Depends

from src.constants.business import Role
from src.controllers.identity import current_user, require
from src.models import calendar
from src.models.database import connect
from src.schemas.calendar import FacilityInput, OutageInput, WindowInput
from src.services import calendar as operations

router = APIRouter(tags=['calendar'])
analyst = require(Role.ANALYST)


@router.get('/facilities')
def facilities(user=Depends(current_user)):
    with connect() as db:
        db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        return calendar.facilities(db)


@router.post('/facilities', status_code=201)
def add_facility(payload: FacilityInput, user=Depends(analyst)):
    return operations.create_facility(payload, user['username'])


@router.post('/facilities/{code}/windows', status_code=201)
def add_opening(code: str, payload: WindowInput, user=Depends(analyst)):
    return operations.save_windows(code, payload, user['username'])


@router.get('/outages')
def outages(user=Depends(current_user)):
    with connect() as db:
        return calendar.outages(db)


@router.post('/outages', status_code=201)
def add_outage(payload: OutageInput, user=Depends(analyst)):
    return operations.create_outage(payload, user['username'])
