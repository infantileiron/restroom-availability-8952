"""节庆临时窗口裁决与核算的纯逻辑测试（不依赖数据库与网络）。

运行：PYTHONPATH=backend python -I backend/tests/test_adjudication.py
"""
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.adjudication import (  # noqa: E402
    adjudicate, apply_adjustments, merge_intervals, subtract_intervals, to_absolute)
from src.services.availability import calculate, opening_intervals  # noqa: E402


def rec(rid, facility, wtype, source, open_date, start_min, end_min, note=''):
    return {'id': rid, 'facility_code': facility, 'window_type': wtype, 'source': source,
            'open_date': open_date, 'start_min': start_min, 'end_min': end_min, 'note': note}


class IntervalTests(unittest.TestCase):
    def test_subtract(self):
        self.assertEqual(subtract_intervals([(0, 100)], [(20, 40), (60, 80)]),
                         [(0, 20), (40, 60), (80, 100)])
        self.assertEqual(subtract_intervals([(0, 100)], [(0, 100)]), [])
        self.assertEqual(merge_intervals([(0, 10), (10, 20), (30, 40)]),
                         [(0, 20), (30, 40)])

    def test_overnight_anchor(self):
        start, end = to_absolute(datetime(2026, 11, 14).date(), 1200, 1620)
        self.assertEqual(start, datetime(2026, 11, 14, 20, 0))
        self.assertEqual(end, datetime(2026, 11, 15, 3, 0))


class PriorityAdjudicationTests(unittest.TestCase):
    def test_holistic_priority_picks_whole_winner(self):
        records = [
            rec(1, 'FJ-02', 'extension', 'festival', '2026-11-14', 1200, 1620),
            rec(2, 'FJ-02', 'reduction', 'hotline', '2026-11-14', 1200, 1320),
        ]
        result = adjudicate(records, 'priority')
        day = result['days']['FJ-02']['2026-11-14']
        # 整体裁决：节庆办整组胜出，热线记录整条被覆盖（120 分钟全丢）
        self.assertEqual(day['winning_intervals'], [(1200, 1620)])
        verdicts = {row['id']: row for row in day['records']}
        self.assertTrue(verdicts[1]['adopted'])
        self.assertEqual(verdicts[1]['adopted_minutes'], 420)
        self.assertFalse(verdicts[2]['adopted'])
        self.assertEqual(verdicts[2]['overridden_minutes'], 120)
        self.assertEqual(verdicts[2]['overridden_by'], [1])
        self.assertEqual(len(day['conflicts']), 1)
        self.assertEqual(day['conflicts'][0]['winning_source'], 'festival')

    def test_non_overlapping_types_coexist(self):
        records = [
            rec(1, 'FJ-01', 'reduction', 'station', '2026-11-14', 0, 360),
            rec(2, 'FJ-01', 'extension', 'station', '2026-11-14', 1320, 1500),
            rec(3, 'FJ-01', 'closed', 'festival', '2026-11-15', 0, 1440),
        ]
        result = adjudicate(records, 'priority')
        d1 = result['days']['FJ-01']['2026-11-14']
        self.assertEqual(d1['winning_intervals'], [(0, 360), (1320, 1500)])
        self.assertEqual(d1['conflicts'], [])
        d2 = result['days']['FJ-01']['2026-11-15']
        self.assertEqual(d2['winning_intervals'], [(0, 1440)])

    def test_three_types_same_day_closed_vs_extension(self):
        # 整日关闭与延长重叠：关闭来源优先级更高则整日关闭胜出
        records = [
            rec(1, 'FJ-03', 'extension', 'hotline', '2026-11-14', 1200, 1320),
            rec(2, 'FJ-03', 'closed', 'festival', '2026-11-14', 0, 1440),
            rec(3, 'FJ-03', 'reduction', 'station', '2026-11-14', 60, 120),
        ]
        result = adjudicate(records, 'priority')
        day = result['days']['FJ-03']['2026-11-14']
        self.assertEqual(day['winning_intervals'], [(0, 1440)])
        self.assertTrue(all(row['window_type'] == 'closed'
                            for row in day['winning_records']))
        self.assertEqual(len(day['conflicts'][0]['group']), 3)


class MinuteAdjudicationTests(unittest.TestCase):
    def test_minute_split_merges_by_priority(self):
        records = [
            rec(1, 'FJ-02', 'extension', 'festival', '2026-11-14', 1200, 1620),
            rec(2, 'FJ-02', 'reduction', 'hotline', '2026-11-14', 1200, 1320),
        ]
        result = adjudicate(records, 'minute')
        day = result['days']['FJ-02']['2026-11-14']
        # 分钟拆分：1200-1320 节庆办胜出，1320-1620 仅节庆办覆盖，合并为一整条
        self.assertEqual(day['winning_intervals'], [(1200, 1620)])
        verdicts = {row['id']: row for row in day['records']}
        self.assertEqual(verdicts[1]['adopted_minutes'], 420)
        self.assertEqual(verdicts[2]['adopted_minutes'], 0)
        self.assertEqual(verdicts[2]['overridden_minutes'], 120)

    def test_minute_split_partial_adoption(self):
        # 低优先级延长在高优先级关闭之外的分钟仍被采用
        records = [
            rec(1, 'FJ-03', 'closed', 'festival', '2026-11-14', 0, 720),
            rec(2, 'FJ-03', 'extension', 'station', '2026-11-14', 600, 900),
        ]
        result = adjudicate(records, 'minute')
        day = result['days']['FJ-03']['2026-11-14']
        self.assertEqual(day['winning_intervals'], [(0, 900)])
        verdicts = {row['id']: row for row in day['records']}
        self.assertEqual(verdicts[2]['adopted_minutes'], 180)   # 720-900
        self.assertEqual(verdicts[2]['overridden_minutes'], 120)  # 600-720
        types = [(row['start_min'], row['window_type']) for row in day['winning_records']]
        self.assertEqual(types, [(0, 'closed'), (720, 'extension')])


class ApplyAdjustmentTests(unittest.TestCase):
    def setUp(self):
        self.anchor = datetime(2026, 11, 14)

    def test_closed_removes_full_day(self):
        planned = [(self.anchor.replace(hour=7), self.anchor.replace(hour=19))]
        out = apply_adjustments(planned, [('closed', (0, 1440))], self.anchor)
        self.assertEqual(out, [])

    def test_extension_adds_and_reduction_cuts(self):
        planned = [(self.anchor.replace(hour=7), self.anchor.replace(hour=19))]
        out = apply_adjustments(planned, [
            ('closed', (0, 360)),
            ('open', (1320, 1500)),
        ], self.anchor)
        self.assertEqual(out, [
            (self.anchor.replace(hour=7), self.anchor.replace(hour=19)),
            (self.anchor.replace(hour=22), self.anchor.replace(day=15, hour=1)),
        ])

    def test_closed_wins_over_extension_overlap(self):
        planned = []
        out = apply_adjustments(planned, [
            ('open', (1200, 1320)),
            ('closed', (0, 1440)),
        ], self.anchor)
        self.assertEqual(out, [])


class CalculateIntegrationTests(unittest.TestCase):
    def _inputs(self, rule_version=None):
        facilities = [{
            'code': 'FJ-02', 'name': '站前夜间公厕', 'district': '站前片区',
            # 每天 20:00-次日02:00
            'windows': [{'weekday': day, 'start_min': 1200, 'end_min': 1560} for day in range(7)],
        }]
        inputs = {'month': '2026-11', 'facilities': facilities, 'outages': []}
        if rule_version:
            inputs['rule_version'] = rule_version
        return inputs

    def test_baseline_without_rule_version_still_works(self):
        result = calculate(self._inputs())
        # 11 月 30 天 × 360 分钟
        self.assertEqual(result['totals']['planned_minutes'], 30 * 360)
        self.assertNotIn('rule_version', result)
        self.assertEqual(result['formula'], 'facility-minute-v2')

    def test_overnight_extension_attribute_to_open_date(self):
        records = [rec(1, 'FJ-02', 'extension', 'festival', '2026-11-14', 1200, 1620)]
        adjudication = adjudicate(records, 'priority')
        rv = {'id': 7, 'label': 'v', 'status': 'active', 'adjudication_mode': 'priority',
              'checksum': 'x', 'adjudication': adjudication}
        result = calculate(self._inputs(rv))
        # 基线 10800，11-14 当天延长 60 分钟（02:00->03:00）
        self.assertEqual(result['totals']['planned_minutes'], 30 * 360 + 60)
        adoption = result['rule_version']['window_adoption']
        self.assertEqual(adoption[0]['starts_at'], '2026-11-14T20:00')
        self.assertEqual(adoption[0]['ends_at'], '2026-11-15T03:00')

    def test_closed_day_zeroes_planned(self):
        records = [rec(1, 'FJ-02', 'closed', 'festival', '2026-11-14', 0, 1440)]
        adjudication = adjudicate(records, 'priority')
        rv = {'id': 7, 'label': 'v', 'status': 'active', 'adjudication_mode': 'priority',
              'checksum': 'x', 'adjudication': adjudication}
        result = calculate(self._inputs(rv))
        self.assertEqual(result['totals']['planned_minutes'], 29 * 360)
        self.assertEqual(result['totals']['excluded_facilities'], 0)
        day = result['facilities'][0]['daily']['2026-11-14']
        self.assertEqual(day['planned'], [])

    def test_conflict_note_carried_to_result(self):
        records = [
            rec(1, 'FJ-02', 'extension', 'festival', '2026-11-14', 1200, 1620),
            rec(2, 'FJ-02', 'reduction', 'hotline', '2026-11-14', 1200, 1320),
        ]
        adjudication = adjudicate(records, 'priority')
        rv = {'id': 7, 'label': 'v', 'status': 'active', 'adjudication_mode': 'priority',
              'checksum': 'x', 'adjudication': adjudication}
        result = calculate(self._inputs(rv))
        self.assertEqual(len(result['rule_version']['conflicts']), 1)
        self.assertEqual(result['rule_version']['conflicts'][0]['facility_code'], 'FJ-02')


if __name__ == '__main__':
    unittest.main(verbosity=2)
