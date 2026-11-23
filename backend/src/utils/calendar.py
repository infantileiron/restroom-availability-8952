from datetime import datetime, time


def month_bounds(month):
    start = datetime.strptime(month, '%Y-%m')
    if start.month == 12:
        return start, datetime(start.year + 1, 1, 1)
    return start, datetime(start.year, start.month + 1, 1)


def minutes(clock: time):
    return clock.hour * 60 + clock.minute
