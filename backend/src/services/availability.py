from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from src.constants.business import FORMULA_VERSION
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

    rows = []
    event_checks = []
    for site in inputs['facilities']:
        plans = opening_intervals(site['windows'], start, end)
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

    totals = metrics(sum(row['planned_minutes'] for row in rows), sum(row['lost_minutes'] for row in rows))
    totals['excluded_facilities'] = sum(row['planned_minutes'] == 0 for row in rows)
    totals['facility_count'] = len(rows)
    return {'totals': totals, 'facilities': rows, 'event_checks': event_checks, 'formula': FORMULA_VERSION}
