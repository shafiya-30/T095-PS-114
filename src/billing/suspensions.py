from datetime import timedelta

from src.billing.late import SUSPEND_AFTER_DAYS


def suspension_episodes(instalments, as_of):
    intervals = []
    for due_date, settled_on in instalments:
        start = due_date + timedelta(days=SUSPEND_AFTER_DAYS)
        if settled_on is not None and settled_on <= as_of:
            end = settled_on
        else:
            end = as_of + timedelta(days=1)
        if end > start:
            intervals.append((start, end))
    intervals.sort()
    episodes = 0
    current_end = None
    for start, end in intervals:
        if current_end is None or start > current_end:
            episodes += 1
            current_end = end
        else:
            current_end = max(current_end, end)
    return episodes