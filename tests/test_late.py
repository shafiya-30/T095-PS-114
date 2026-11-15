from datetime import date
from decimal import Decimal

from src.billing.late import (
    can_choose_plan_4,
    days_overdue,
    is_suspended,
    late_fee,
)

DUE = date(2026, 5, 25)


def after(days):
    return date.fromordinal(DUE.toordinal() + days)


def test_not_overdue_before_due_date():
    assert days_overdue(DUE, after(-3)) == 0
    assert late_fee(DUE, after(-3)) == Decimal("0.00")


def test_no_late_fee_inside_10_day_grace():
    assert late_fee(DUE, DUE) == Decimal("0.00")
    assert late_fee(DUE, after(10)) == Decimal("0.00")


def test_late_fee_starts_on_day_11():
    assert late_fee(DUE, after(11)) == Decimal("100.00")
    assert late_fee(DUE, after(12)) == Decimal("200.00")


def test_late_fee_at_30_days_matches_enr_0001():
    assert late_fee(DUE, date(2026, 6, 24)) == Decimal("2000.00")


def test_late_fee_capped_at_3000():
    assert late_fee(DUE, after(40)) == Decimal("3000.00")
    assert late_fee(DUE, after(200)) == Decimal("3000.00")


def test_late_fee_of_paid_instalment_stops_at_payment_date():
    assert late_fee(DUE, date(2026, 7, 31), paid_on=date(2026, 6, 24)) == Decimal("2000.00")


def test_late_fee_ignores_payment_made_after_as_of_date():
    assert late_fee(DUE, after(15), paid_on=after(40)) == Decimal("500.00")


def test_not_suspended_at_29_days():
    assert is_suspended(DUE, after(29)) is False


def test_suspended_at_exactly_30_days_when_unpaid():
    assert is_suspended(DUE, after(30)) is True


def test_payment_on_day_30_prevents_suspension():
    assert is_suspended(DUE, after(30), paid_on=after(30)) is False


def test_payment_after_as_of_date_does_not_prevent_suspension():
    assert is_suspended(DUE, after(35), paid_on=after(40)) is True


def test_paid_instalment_is_not_suspended_later():
    assert is_suspended(DUE, date(2026, 7, 31), paid_on=date(2026, 6, 24)) is False


def test_two_suspensions_lose_the_4_instalment_option():
    assert can_choose_plan_4(0) is True
    assert can_choose_plan_4(1) is True
    assert can_choose_plan_4(2) is False
    assert can_choose_plan_4(3) is False