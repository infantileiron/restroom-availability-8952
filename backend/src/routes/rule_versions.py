from fastapi import APIRouter, Depends

from src.constants.business import Role
from src.controllers.identity import current_user, require
from src.schemas.rule_versions import RuleVersionInput, TempWindowInput
from src.services import rule_versions as operations

router = APIRouter(prefix='/rule-versions', tags=['rule-versions'])
analyst = require(Role.ANALYST)


@router.get('')
def versions(user=Depends(current_user)):
    return operations.list_versions(user)


@router.post('', status_code=201)
def create_version(payload: RuleVersionInput, user=Depends(analyst)):
    return operations.create_version(payload, user['username'])


@router.get('/{version_id}')
def version_detail(version_id: int, user=Depends(current_user)):
    return operations.detail(version_id, user)


@router.get('/{version_id}/preview')
def preview(version_id: int, user=Depends(current_user)):
    return operations.preview(version_id, user)


@router.post('/{version_id}/activate', status_code=200)
def activate(version_id: int, user=Depends(analyst)):
    return operations.activate(version_id, user['username'])


@router.post('/{version_id}/windows', status_code=201)
def add_window(version_id: int, payload: TempWindowInput, user=Depends(analyst)):
    return operations.add_window(version_id, payload, user['username'])


@router.delete('/{version_id}/windows/{window_id}', status_code=200)
def remove_window(version_id: int, window_id: int, user=Depends(analyst)):
    return operations.remove_window(version_id, window_id, user['username'])
