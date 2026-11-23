from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from src.constants.business import FORMULA_VERSION
from src.services.adjudication import apply_adjustments
from src.utils.calendar import month_bounds

DAY = timedelta(days=1)
MINUTE = timedelta(minutes=1)


def union(intervals):
    merged = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        elif end > merged[-1][1]:
            merged[-1] = (merged[-1][0], end)
    return merged


def intersections(left, right):
    i = j = 0
    while i < len(left) and j < len(right):
        left_start, left_end = left[i]
        right_start, right_end = right[j]
        start, end = max(left_start, right_start), min(left_end, right_end)
        if start < end:
            yield start, end
        if left_end <= right_end:
            i += 1
        else:
            j += 1


def duration(intervals):
    return sum((end - start) // MINUTE for start, end in intervals)


def opening_intervals(windows, start, end):
    by_weekday = defaultdict(list)
    for rule in windows:
        by_weekday[rule['weekday']].append(rule)
    intervals = []
    day = start - DAY
    while day < end:
        for rule in by_weekday[day.weekday()]:
            open_at = max(start, day + rule['start_min'] * MINUTE)
            close_at = min(end, day + rule['end_min'] * MINUTE)
            if open_at < close_at:
                intervals.append((open_at, close_at))
        day += DAY
    return union(intervals)


def _festival_index(rule_version):
    """把冻结版本的裁决结果整理成 facility -> open_date(iso) -> day_result。"""
    if not rule_version:
        return {}
    index = {}
    for facility_code, days in rule_version['adjudication']['days'].items():
        index[facility_code] = {open_date: day for open_date, day in days.items()}
    return index


def adjusted_plans(base_plans, festival_days, start, end):
    """在常设周计划上按开门日套用节庆临时窗口（跨夜部分归属开门日）。"""
    if not festival_days:
        return base_plans, []
    adoption = []
    result = list(base_plans)
    for open_date, day_result in sorted(festival_days.items()):
        anchor = datetime.combine(datetime.fromisoformat(open_date).date(),
                                  datetime.min.time())
        adjustments = [
            ('closed' if entry['window_type'] in ('closed', 'reduction') else 'open',
             (entry['start_min'], entry['end_min']))
            for entry in day_result['winning_records']]
        result = apply_adjustments(result, adjustments, anchor)
        for entry in day_result['winning_records']:
            win_start = anchor + entry['start_min'] * MINUTE
            win_end = anchor + entry['end_min'] * MINUTE
            clip_start, clip_end = max(win_start, start), min(win_end, end)
            if clip_start >= clip_end:
                continue  # 采用窗口完全落在核算月外，不计入本月说明
            adoption.append({'open_date': open_date, **entry,
                             'starts_at': clip_start.isoformat(timespec='minutes'),
                             'ends_at': clip_end.isoformat(timespec='minutes')})
    clipped = [(max(a, start), min(b, end)) for a, b in result]
    return [(a, b) for a, b in clipped if a < b], adoption


def metrics(planned, lost):
    available = planned - lost
    rate = None
    if planned:
        rate = str((Decimal(available * 100) / planned).quantize(Decimal('0.01'), ROUND_HALF_UP))
    return {'planned_minutes': planned, 'lost_minutes': lost, 'available_minutes': available,
            'availability_pct': rate}


def daily_timeline(plans, losses, start, end):
    days = {}
    while start < end:
        next_day = start + DAY
        clip = [(start, next_day)]
        days[start.date().isoformat()] = {
            key: [[(a - start) // MINUTE, (b - start) // MINUTE]
                  for a, b in intersections(intervals, clip)]
            for key, intervals in [('planned', plans), ('lost', losses)]
        }
        start = next_day
    return days


def calculate(inputs):
    start, end = month_bounds(inputs['month'])
    period = [(start, end)]
    events_by_site = defaultdict(list)
    for event in inputs['outages']:
        interval = (datetime.fromisoformat(event['starts_at']), datetime.fromisoformat(event['ends_at']))
        events_by_site[event['facility_code']].append((event['code'], interval))

    festival = _festival_index(inputs.get('rule_version'))
    rule_version = inputs.get('rule_version')
    rows = []
    event_checks = []
    window_adoption = []
    conflict_notes = []
    for site in inputs['facilities']:
        base = opening_intervals(site['windows'], start, end)
        plans, adoption = adjusted_plans(base, festival.get(site['code'], {}), start, end)
        for item in adoption:
            window_adoption.append({'facility_code': site['code'], 'facility_name': site['name'], **item})
        events = events_by_site[site['code']]
        reported = list(intersections(union(interval for _, interval in events), period))
        losses = list(intersections(plans, reported))
        planned, lost = duration(plans), duration(losses)
        for code, interval in events:
            in_month = list(intersections([interval], period))
            event_checks.append({'code': code, 'facility_code': site['code'],
                                 'in_month_minutes': duration(in_month),
                                 'inside_opening_minutes': duration(intersections(plans, in_month))})
        rows.append({'code': site['code'], 'name': site['name'], 'district': site['district'],
                     **metrics(planned, lost), 'out_of_window_minutes': duration(reported) - lost,
                     'daily': daily_timeline(plans, losses, start, end)})

    if rule_version:
        for facility_code, days in rule_version['adjudication']['days'].items():
            for open_date, day_result in days.items():
                for conflict in day_result['conflicts']:
                    conflict_notes.append({'facility_code': facility_code, 'open_date': open_date,
                                           **conflict})

    totals = metrics(sum(row['planned_minutes'] for row in rows), sum(row['lost_minutes'] for row in rows))
    totals['excluded_facilities'] = sum(row['planned_minutes'] == 0 for row in rows)
    totals['facility_count'] = len(rows)
    result = {'totals': totals, 'facilities': rows, 'event_checks': event_checks,
              'formula': FORMULA_VERSION}
    if rule_version:
        result['rule_version'] = {
            'id': rule_version['id'], 'label': rule_version['label'],
            'status': rule_version['status'], 'adjudication_mode': rule_version['adjudication_mode'],
            'checksum': rule_version['checksum'],
            'window_adoption': window_adoption, 'conflicts': conflict_notes,
        }
    return result
