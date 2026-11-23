from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from src.constants.business import Role, Status
from src.controllers.identity import current_user, require
from src.schemas.snapshots import SnapshotInput
from src.services import snapshots
from src.services.exports import export_path

router = APIRouter(prefix='/snapshots', tags=['snapshots'])


@router.get('')
def list_snapshots(user=Depends(current_user)):
    return snapshots.list_visible(user)


@router.post('', status_code=201)
def capture(payload: SnapshotInput, user=Depends(require(Role.ANALYST))):
    return snapshots.capture(payload, user['username'])


@router.get('/{snapshot_id}')
def detail(snapshot_id: int, user=Depends(current_user)):
    return snapshots.detail(snapshot_id, user)


@router.post('/{snapshot_id}/run', status_code=202)
def execute(snapshot_id: int, user=Depends(require(Role.ANALYST))):
    return snapshots.transition(snapshot_id, user['username'], 'run')


@router.post('/{snapshot_id}/publish')
def publish(snapshot_id: int, user=Depends(require(Role.REVIEWER))):
    return snapshots.transition(snapshot_id, user['username'], 'publish')


@router.get('/{snapshot_id}/export')
def export(snapshot_id: int, user=Depends(current_user)):
    snapshot = snapshots.detail(snapshot_id, user)
    if snapshot['status'] not in (Status.READY, Status.PUBLISHED):
        raise HTTPException(409, '请先完成核算')
    path = export_path(snapshot_id)
    if not path.is_file():
        raise HTTPException(503, '暂时无法读取导出文件')
    return FileResponse(path, media_type='text/csv; charset=utf-8', filename=f"开放时段-{snapshot['month']}-V{snapshot_id}.csv")
