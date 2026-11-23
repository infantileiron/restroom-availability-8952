"""核算 + 导出的端到端纯逻辑测试（不依赖数据库与网络）。

运行：PYTHONPATH=backend python -I backend/tests/test_export_pipeline.py
"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / 'tests' / '_vendorstub'))
sys.path.insert(0, str(BACKEND))
from src.services import exports  # noqa: E402
from src.services.adjudication import adjudicate  # noqa: E402
from src.services.availability import calculate  # noqa: E402


def rec(rid, facility, wtype, source, open_date, start_min, end_min, note=''):
    return {'id': rid, 'facility_code': facility, 'window_type': wtype, 'source': source,
            'open_date': open_date, 'start_min': start_min, 'end_min': end_min, 'note': note}


def build_inputs():
    windows = {
        'FJ-01': [(0, 1440)],          # 桥西全天
        'FJ-02': [(1200, 1560), (1290, 1380)],  # 站前夜间，含重叠
        'FJ-03': [(420, 1140)],        # 河畔 07-19
    }
    facilities = []
    names = {'FJ-01': '桥西便民公厕', 'FJ-02': '站前夜间公厕', 'FJ-03': '河畔绿道公厕'}
    for code, rules in windows.items():
        facilities.append({'code': code, 'name': names[code], 'district': code,
                           'windows': [{'weekday': d, 'start_min': s, 'end_min': e}
                                       for s, e in rules for d in range(7)]})
    records = [
        rec(1, 'FJ-02', 'extension', 'festival', '2026-11-14', 1200, 1620, '灯会延长跨夜'),
        rec(2, 'FJ-02', 'reduction', 'hotline', '2026-11-14', 1200, 1320, '热线缩短'),
        rec(3, 'FJ-03', 'closed', 'festival', '2026-11-14', 0, 1440, '整日关闭'),
    ]
    adjudication = adjudicate(records, 'priority')
    rule_version = {'id': 3, 'label': '十一月节庆·一版', 'status': 'active',
                    'adjudication_mode': 'priority', 'checksum': 'a' * 64,
                    'adjudication': adjudication}
    return {'month': '2026-11', 'facilities': facilities, 'outages': [],
            'rule_version': rule_version}


class ExportPipelineTests(unittest.TestCase):
    def test_full_pipeline_and_csvs(self):
        inputs = build_inputs()
        result = calculate(inputs)
        self.assertEqual(result['formula'], 'facility-minute-v2')
        # 站前：基线 30*360=10800，11-14 延长 60 分钟；热线缩短被整体裁决覆盖
        f2 = next(row for row in result['facilities'] if row['code'] == 'FJ-02')
        self.assertEqual(f2['planned_minutes'], 10800 + 60)
        # 河畔：基线 30*720，11-14 整日关闭扣 720
        f3 = next(row for row in result['facilities'] if row['code'] == 'FJ-03')
        self.assertEqual(f3['planned_minutes'], 30 * 720 - 720)
        self.assertEqual(f3['daily']['2026-11-14']['planned'], [])
        # 跨夜归属：11-14 的延长延伸到 11-15 03:00
        adoption = result['rule_version']['window_adoption']
        f2_adopt = next(a for a in adoption if a['facility_code'] == 'FJ-02')
        self.assertEqual(f2_adopt['ends_at'], '2026-11-15T03:00')
        self.assertEqual(len(result['rule_version']['conflicts']), 1)

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(exports, 'ARTIFACT_DIR', Path(tmp)):
                exports.write_export(9, inputs, 'b' * 64, result)
                main_csv = Path(tmp) / 'availability-9.csv'
                win_csv = Path(tmp) / 'festival-windows-9.csv'
                self.assertTrue(main_csv.is_file() and win_csv.is_file())
                with main_csv.open(encoding='utf-8-sig') as stream:
                    rows = list(csv.DictReader(stream))
                self.assertIn('rule_version_label', rows[0])
                self.assertEqual(rows[0]['rule_version_id'], 'V3')
                self.assertEqual(rows[-1]['code'], 'TOTAL')
                with win_csv.open(encoding='utf-8-sig') as stream:
                    win_rows = list(csv.DictReader(stream))
                sections = {row['section'] for row in win_rows}
                self.assertEqual(sections, {'采用窗口', '冲突裁决'})
                conflict = next(row for row in win_rows if row['section'] == '冲突裁决')
                self.assertEqual(conflict['winning_source'], '节庆办通知')
                self.assertEqual(conflict['overridden_record_ids'], '2')

    def test_legacy_inputs_without_rule_version(self):
        inputs = build_inputs()
        inputs.pop('rule_version')
        result = calculate(inputs)
        self.assertNotIn('rule_version', result)
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(exports, 'ARTIFACT_DIR', Path(tmp)):
                exports.write_export(11, inputs, 'c' * 64, result)
                with (Path(tmp) / 'availability-11.csv').open(encoding='utf-8-sig') as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual(rows[0]['rule_version_label'], '无节庆临时窗口（仅常设周规则）')
                self.assertFalse((Path(tmp) / 'festival-windows-11.csv').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
