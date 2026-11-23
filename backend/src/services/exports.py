import csv
from pathlib import Path
from tempfile import NamedTemporaryFile

from src.config.runtime import ARTIFACT_DIR

COLUMNS = ('month', 'snapshot_id', 'formula', 'checksum', 'code', 'name', 'district',
           'planned_minutes', 'lost_minutes', 'available_minutes', 'availability_pct', 'out_of_window_minutes')


def export_path(snapshot_id):
    return ARTIFACT_DIR / f'availability-{snapshot_id}.csv'


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def write_export(snapshot_id, inputs, checksum, result):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = None
    try:
        with NamedTemporaryFile(dir=ARTIFACT_DIR, encoding='utf-8-sig', newline='', mode='w', delete=False) as stream:
            path = Path(stream.name)
            writer = csv.writer(stream)
            writer.writerow(COLUMNS)
            summary = {**result['totals'], 'code': 'TOTAL', 'name': '全辖区'}
            for row in [*result['facilities'], summary]:
                cells = dict(row, month=inputs['month'], snapshot_id=snapshot_id,
                             formula=result['formula'], checksum=checksum)
                writer.writerow(safe_cell(cells.get(key)) for key in COLUMNS)
        path.replace(export_path(snapshot_id))
    finally:
        if path is not None:
            path.unlink(missing_ok=True)
