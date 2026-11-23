import hashlib
import json

from fastapi import HTTPException

from src.models import rule_versions as store
from src.models.audit import audit
from src.models.database import connect
from src.services.adjudication import adjudicate


def _serialize_window(window):
    row = dict(window)
    row['open_date'] = row['open_date'].isoformat()
    return row


def create_version(payload, actor):
    with connect() as db:
        row = store.create_version(db, payload.label, payload.adjudication_mode.value, actor)
        audit(db, actor, 'rule_version.create', row['id'])
        return row


def list_versions(_user):
    with connect() as db:
        return store.list_versions(db)


def detail(version_id, _user):
    with connect() as db:
        version = store.get_version(db, version_id)
        if not version:
            raise HTTPException(404, '找不到这个规则版本')
        version = dict(version)
        version['windows'] = [_serialize_window(row) for row in store.list_windows(db, version_id)]
        return version


def add_window(version_id, payload, actor):
    with connect() as db:
        version = store.get_version(db, version_id, for_update=True)
        if not version:
            raise HTTPException(404, '找不到这个规则版本')
        if version['status'] != 'draft':
            raise HTTPException(409, '已激活版本不可变更，请新建规则版本录入')
        if not db.execute('SELECT 1 FROM facilities WHERE code = %s',
                          (payload.facility_code,)).fetchone():
            raise HTTPException(404, '设施不存在')
        row = store.insert_window(db, payload, version_id, actor)
        if row:
            audit(db, actor, 'temp_window.add', row['id'])
            return {'added': row['id'], 'duplicated': False}
        audit(db, actor, 'temp_window.dedupe', f'{version_id}:{payload.facility_code}')
        return {'added': None, 'duplicated': True}


def remove_window(version_id, window_id, actor):
    with connect() as db:
        version = store.get_version(db, version_id, for_update=True)
        if not version:
            raise HTTPException(404, '找不到这个规则版本')
        if version['status'] != 'draft':
            # 已冻结快照沿用当时规则；任何已激活记录都不能删除，丢失即无法恢复。
            raise HTTPException(409, '已激活版本的记录受保护，不能删除')
        window = store.find_window(db, window_id, version_id)
        if not window:
            raise HTTPException(404, '找不到这条临时窗口记录')
        store.delete_window(db, window_id)
        audit(db, actor, 'temp_window.delete', window_id)
        return {'deleted': window_id}


def preview(version_id, _user):
    with connect() as db:
        version = store.get_version(db, version_id)
        if not version:
            raise HTTPException(404, '找不到这个规则版本')
        records = [_serialize_window(row) for row in store.list_windows(db, version_id)]
    return adjudicate(records, version['adjudication_mode'])


def activate(version_id, actor):
    """激活在单事务内完成：裁决、校验和、新旧版本切换。

    事务中途失败整体回滚，当前旧 active 版本继续生效；重复激活同一版本
    直接返回现状，不重复计算也不覆盖。
    """
    with connect() as db:
        version = store.get_version(db, version_id, for_update=True)
        if not version:
            raise HTTPException(404, '找不到这个规则版本')
        if version['status'] == 'active':
            return {'id': version_id, 'idempotent': True, 'checksum': version['checksum']}
        records = [_serialize_window(row) for row in store.list_windows(db, version_id)]
        if not records:
            raise HTTPException(422, '空版本不能激活，请先录入节庆临时窗口')
        result = adjudicate(records, version['adjudication_mode'])
        canonical = json.dumps({'mode': result['mode'], 'records': records},
                               sort_keys=True, separators=(',', ':'),
                               ensure_ascii=False).encode()
        checksum = hashlib.sha256(canonical).hexdigest()
        store.activate(db, version_id, actor, result, checksum)
        audit(db, actor, 'rule_version.activate', version_id)
        return {'id': version_id, 'idempotent': False, 'checksum': checksum}
