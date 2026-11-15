from decimal import Decimal

GRACE_DAYS = 10
LATE_FEE_PER_DAY = Decimal("100.00")
LATE_FEE_CAP = Decimal("3000.00")
SUSPEND_AFTER_DAYS = 30
SUSPENSIONS_BEFORE_PLAN_4_LOST = 2


def days_overdue(due_date, as_of):
    return max(0, (as_of - due_date).days)


def late_fee(due_date, as_of, paid_on=None):
    reference = min(paid_on, as_of) if paid_on else as_of
    chargeable = max(0, days_overdue(due_date, reference) - GRACE_DAYS)
    return min(LATE_FEE_CAP, LATE_FEE_PER_DAY * chargeable)


def is_suspended(due_date, as_of, paid_on=None):
    if paid_on is not None and paid_on <= as_of:
        return False
    return days_overdue(due_date, as_of) >= SUSPEND_AFTER_DAYS


def can_choose_plan_4(times_suspended):
    return times_suspended < SUSPENSIONS_BEFORE_PLAN_4_LOST