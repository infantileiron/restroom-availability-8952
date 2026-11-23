"""节庆临时窗口的归一化与冲突裁决（纯逻辑，不依赖数据库）。

同一公厕同一天可同时存在延长、缩短和整日关闭记录。跨夜窗口以开门日
（open_date）归属，分钟坐标与周规则一致：0–1440 为开门日，超过 1440
的部分落在次日，最长 24 小时。

两种裁决方式：
- priority：冲突记录按来源优先级整体裁决，同组最高优先级来源的记录整组胜出；
- minute：按分钟拆分合并，每个分钟取覆盖它的最高优先级记录，再合并回区间。
"""
from collections import defaultdict
from datetime import datetime, timedelta

from src.constants.business import SOURCE_PRIORITY, AdjudicationMode, RuleSource

MINUTE = timedelta(minutes=1)


def merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        elif end > merged[-1][1]:
            merged[-1][1] = end
    return [(start, end) for start, end in merged]


def subtract_intervals(base, cuts):
    """从 base 的各区间中切掉 cuts 覆盖的部分。"""
    remaining = []
    for b_start, b_end in base:
        pieces = [(b_start, b_end)]
        for c_start, c_end in sorted(cuts):
            next_pieces = []
            for p_start, p_end in pieces:
                if c_end <= p_start or c_start >= p_end:
                    next_pieces.append((p_start, p_end))
                else:
                    if c_start > p_start:
                        next_pieces.append((p_start, c_start))
                    if c_end < p_end:
                        next_pieces.append((c_end, p_end))
            pieces = next_pieces
        remaining.extend(pieces)
    return merge_intervals(remaining)


def _record_key(record):
    return (record['facility_code'], record['open_date'])


def _record_rank(record):
    """同优先级时的确定性次序：先登记的记录排前。"""
    return (-SOURCE_PRIORITY[RuleSource(record['source'])], record['id'])


def _conflict_groups(records):
    """把互相交叠（含端点相接以外的任意分钟重叠）的记录归为同一冲突组。"""
    ordered = sorted(records, key=lambda r: (r['start_min'], r['end_min'], r['id']))
    groups = []
    for record in ordered:
        placed = None
        for group in groups:
            if any(not (record['end_min'] <= other['start_min']
                        or record['start_min'] >= other['end_min']) for other in group):
                if placed is None:
                    group.append(record)
                    placed = group
                else:
                    placed.extend(group)
                    group.clear()
        if placed is None:
            groups.append([record])
    return [group for group in groups if group]


def _adjudicate_priority(records):
    groups = _conflict_groups(records)
    winning_intervals = []
    verdicts = {record['id']: {'record_id': record['id'], 'adopted_minutes': 0,
                               'overridden_minutes': record['end_min'] - record['start_min'],
                               'adopted': False, 'decided_by': 'overridden',
                               'overridden_by': []}
                for record in records}
    conflict_report = []
    for group in groups:
        winner = sorted(group, key=_record_rank)[0]
        winner_ids = {r['id'] for r in group
                      if r['source'] == winner['source']
                      and SOURCE_PRIORITY[RuleSource(r['source'])]
                      == SOURCE_PRIORITY[RuleSource(winner['source'])]}
        winners = [r for r in group if r['id'] in winner_ids]
        losers = [r for r in group if r['id'] not in winner_ids]
        for record in winners:
            length = record['end_min'] - record['start_min']
            verdicts[record['id']].update(
                adopted=True, adopted_minutes=length, overridden_minutes=0,
                decided_by='priority', overridden_by=[])
            winning_intervals.append((record['start_min'], record['end_min'], record['id']))
        for record in losers:
            verdicts[record['id']]['overridden_by'] = sorted(winner_ids)
        if losers:
            conflict_report.append({
                'group': sorted(r['id'] for r in group),
                'mode': 'priority',
                'winning_source': winner['source'],
                'winning_record_ids': sorted(winner_ids),
                'overridden_record_ids': sorted(r['id'] for r in losers),
                'reason': f"来源优先级 {RuleSource(winner['source']).value} 高于其他来源，整组采用",
            })
    winning_intervals = merge_intervals((start, end) for start, end, _ in winning_intervals)
    return winning_intervals, verdicts, conflict_report, groups, None


def _adjudicate_minute(records):
    # 收集所有边界，按分钟段扫描，避免逐分钟循环。
    cuts = sorted({bound for record in records for bound in (record['start_min'], record['end_min'])})
    winning_runs = []
    wins = defaultdict(int)
    overridden_by = defaultdict(set)
    for left, right in zip(cuts, cuts[1:]):
        covering = [record for record in records
                    if record['start_min'] <= left and record['end_min'] >= right]
        if not covering:
            continue
        winner = sorted(covering, key=_record_rank)[0]
        wins[winner['id']] += right - left
        for record in covering:
            if record['id'] != winner['id']:
                overridden_by[record['id']].add(winner['id'])
        if winning_runs and winning_runs[-1][2] == winner['id'] and winning_runs[-1][1] == left:
            winning_runs[-1][1] = right
        else:
            winning_runs.append([left, right, winner['id']])
    winning_intervals = merge_intervals((start, end) for start, end, _ in winning_runs)
    verdicts = {}
    for record in records:
        length = record['end_min'] - record['start_min']
        adopted = wins.get(record['id'], 0)
        verdicts[record['id']] = {
            'record_id': record['id'], 'adopted_minutes': adopted,
            'overridden_minutes': length - adopted,
            'adopted': adopted > 0, 'decided_by': 'minute',
            'overridden_by': sorted(overridden_by.get(record['id'], ())),
        }
    groups = _conflict_groups(records)
    conflict_report = [{
        'group': sorted(r['id'] for r in group),
        'mode': 'minute',
        'winning_record_ids': sorted(rid for rid, count in wins.items()
                                     if count and any(r['id'] == rid for r in group)),
        'overridden_record_ids': sorted(r['id'] for r in group if not wins.get(r['id'], 0)),
        'reason': '按分钟拆分，每分钟取最高优先级来源后再合并',
    } for group in groups if len(group) > 1]
    return winning_intervals, verdicts, conflict_report, groups, winning_runs


def adjudicate(raw_records, mode):
    """对一个版本的全部临时窗口做归一化裁决。

    返回结构按 facility_code / open_date 分组，每组保留：
    - winning_intervals：最终采用的分钟区间（合并后，不带类型）；
    - winning_records：采用区间分别由哪条记录、以什么窗口类型生效；
    - records：每条原始记录的采用/被覆盖裁决结果（记录不丢失）；
    - conflicts：冲突组与裁决说明。
    """
    mode = AdjudicationMode(mode)
    grouped = defaultdict(list)
    for raw in raw_records:
        record = dict(raw)
        open_date = record['open_date']
        if hasattr(open_date, 'isoformat'):
            record['open_date'] = open_date.isoformat()
        grouped[_record_key(record)].append(record)

    result = {'mode': mode.value, 'days': {}}
    for (facility_code, open_date), records in sorted(grouped.items()):
        if mode == AdjudicationMode.PRIORITY:
            winning_intervals, verdicts, conflicts, _groups, _runs = _adjudicate_priority(records)
            winning_records = [
                {'start_min': record['start_min'], 'end_min': record['end_min'],
                 'window_type': record['window_type'], 'source': record['source'],
                 'record_id': record['id']}
                for record in sorted(records, key=lambda r: r['id'])
                if verdicts[record['id']]['adopted']
            ]
        else:
            winning_intervals, verdicts, conflicts, _groups, winning_runs = _adjudicate_minute(records)
            winning_records = [
                {'start_min': start, 'end_min': end,
                 'window_type': next(r['window_type'] for r in records if r['id'] == record_id),
                 'source': next(r['source'] for r in records if r['id'] == record_id),
                 'record_id': record_id}
                for start, end, record_id in winning_runs
            ]
        result['days'].setdefault(facility_code, {})[open_date] = {
            'winning_intervals': winning_intervals,
            'winning_records': winning_records,
            'records': [_record_view(record, verdicts[record['id']]) for record in records],
            'conflicts': conflicts,
        }
    return result


def _record_view(record, verdict):
    view = {key: record[key] for key in
            ('id', 'window_type', 'source', 'open_date', 'start_min', 'end_min', 'note')}
    view.update(verdict)
    return view


def to_absolute(open_date, start_min, end_min):
    """开门日相对分钟 -> 绝对时间区间，跨夜部分自然落到次日。"""
    anchor = datetime.combine(open_date, datetime.min.time())
    return anchor + start_min * MINUTE, anchor + end_min * MINUTE


def apply_adjustments(planned, adjustments, day_anchor):
    """在常设周计划区间上套用整日的临时调整。

    closed（整日关闭/缩短）先从计划中扣除，open（延长）再并回；
    最终再扣一次 closed，保证关闭与延长重叠时关闭优先。
    """
    closed, opened = [], []
    for kind, (start_min, end_min) in adjustments:
        absolute = (day_anchor + start_min * MINUTE, day_anchor + end_min * MINUTE)
        (closed if kind == 'closed' else opened).append(absolute)
    result = subtract_intervals(planned, closed)
    result = merge_intervals([*result, *opened])
    return subtract_intervals(result, closed)
