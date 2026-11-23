import csv
from pathlib import Path
from tempfile import NamedTemporaryFile

from src.config.runtime import ARTIFACT_DIR

COLUMNS = ('month', 'snapshot_id', 'formula', 'checksum', 'code', 'name', 'district',
           'planned_minutes', 'lost_minutes', 'available_minutes', 'availability_pct',
           'out_of_window_minutes', 'rule_version_id', 'rule_version_label',
           'adjudication_mode', 'rule_checksum')

WINDOW_COLUMNS = ('month', 'snapshot_id', 'section', 'facility_code', 'facility_name',
                  'open_date', 'window_type', 'source', 'starts_at', 'ends_at',
                  'record_id', 'adopted_minutes', 'overridden_minutes', 'decided_by',
                  'conflict_group', 'winning_source', 'winning_record_ids',
                  'overridden_record_ids', 'reason')

WINDOW_TYPE_LABEL = {'extension': '延长开放', 'reduction': '缩短开放', 'closed': '整日关闭'}
SOURCE_LABEL = {'festival': '节庆办通知', 'station': '环卫站调度', 'hotline': '值班热线登记'}
MODE_LABEL = {'priority': '来源优先级整体裁决', 'minute': '按分钟拆分合并'}


def export_path(snapshot_id):
    return ARTIFACT_DIR / f'availability-{snapshot_id}.csv'


def window_export_path(snapshot_id):
    return ARTIFACT_DIR / f'festival-windows-{snapshot_id}.csv'


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def _rule_cells(inputs, result):
    rule = result.get('rule_version')
    if not rule:
        return {'rule_version_id': '', 'rule_version_label': '无节庆临时窗口（仅常设周规则）',
                'adjudication_mode': '', 'rule_checksum': ''}
    return {'rule_version_id': f"V{rule['id']}", 'rule_version_label': rule['label'],
            'adjudication_mode': MODE_LABEL.get(rule['adjudication_mode'], rule['adjudication_mode']),
            'rule_checksum': rule['checksum']}


def write_export(snapshot_id, inputs, checksum, result):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = None
    rule_cells = _rule_cells(inputs, result)
    try:
        with NamedTemporaryFile(dir=ARTIFACT_DIR, encoding='utf-8-sig', newline='', mode='w', delete=False) as stream:
            path = Path(stream.name)
            writer = csv.writer(stream)
            writer.writerow(COLUMNS)
            summary = {**result['totals'], 'code': 'TOTAL', 'name': '全辖区'}
            for row in [*result['facilities'], summary]:
                cells = dict(row, month=inputs['month'], snapshot_id=snapshot_id,
                             formula=result['formula'], checksum=checksum, **rule_cells)
                writer.writerow(safe_cell(cells.get(key)) for key in COLUMNS)
        path.replace(export_path(snapshot_id))
    finally:
        if path is not None:
            path.unlink(missing_ok=True)
    if result.get('rule_version'):
        write_window_export(snapshot_id, inputs, result)


def write_window_export(snapshot_id, inputs, result):
    """逐行写清采用的窗口以及每条冲突的裁决结果，记录不丢失。"""
    rule = result['rule_version']
    adoption_index = {(item['facility_code'], item['open_date'], item['record_id']): item
                      for item in rule['window_adoption']}
    path = None
    try:
        with NamedTemporaryFile(dir=ARTIFACT_DIR, encoding='utf-8-sig', newline='', mode='w', delete=False) as stream:
            path = Path(stream.name)
            writer = csv.writer(stream)
            writer.writerow(WINDOW_COLUMNS)
            for item in rule['window_adoption']:
                writer.writerow(safe_cell(value) for value in (
                    inputs['month'], snapshot_id, '采用窗口', item['facility_code'],
                    item['facility_name'], item['open_date'],
                    WINDOW_TYPE_LABEL.get(item['window_type'], item['window_type']),
                    SOURCE_LABEL.get(item['source'], item['source']),
                    item['starts_at'], item['ends_at'], item['record_id'],
                    '', '', '', '', '', '', '', ''))
            for conflict in rule['conflicts']:
                writer.writerow(safe_cell(value) for value in (
                    inputs['month'], snapshot_id, '冲突裁决', conflict['facility_code'], '',
                    conflict['open_date'], '', '', '', '', '', '', '',
                    MODE_LABEL.get(rule['adjudication_mode'], rule['adjudication_mode']),
                    '|'.join(str(rid) for rid in conflict['group']),
                    SOURCE_LABEL.get(conflict.get('winning_source', ''), conflict.get('winning_source', '')),
                    '|'.join(str(rid) for rid in conflict['winning_record_ids']),
                    '|'.join(str(rid) for rid in conflict.get('overridden_record_ids', [])),
                    conflict['reason']))
        path.replace(window_export_path(snapshot_id))
    finally:
        if path is not None:
            path.unlink(missing_ok=True)
