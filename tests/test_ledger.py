from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.billing.fees import compute_fee, load_courses
from src.billing.ledger import Ledger
from src.billing.schedule import build_schedule

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def courses():
    return load_courses(DATA / "courses.csv")


def ledger_for(course, waiver, sibling, plan, enrol_date):
    fee = compute_fee(course, waiver, sibling, plan)
    ledger = Ledger(build_schedule(fee, plan, enrol_date))
    ledger.pay(ledger.items[0].instalment.amount, enrol_date)
    return ledger


def test_first_instalment_is_paid_with_enrolment(courses):
    ledger = ledger_for(courses["FOUND-1Y"], 0, False, 2, date(2026, 3, 26))
    assert ledger.items[0].settled_on == date(2026, 3, 26)
    assert ledger.items[1].settled_on is None
    assert ledger.settled_count() == 1


def test_payment_with_late_fee_settles_second_instalment_matches_enr_0001(courses):
    ledger = ledger_for(courses["FOUND-1Y"], 0, True, 2, date(2026, 3, 26))
    leftover = ledger.pay(Decimal("61590.00"), date(2026, 6, 24))
    second = ledger.items[1]
    assert leftover == Decimal("0.00")
    assert second.paid == Decimal("61590.00")
    assert second.late_fee_charged == Decimal("2000.00")
    assert ledger.balance_on(date(2026, 7, 31)) == Decimal("0.00")
    assert ledger.access_status(date(2026, 7, 31)) == "ACTIVE"


def test_payment_on_day_30_overdue_is_not_suspended(courses):
    ledger = ledger_for(courses["FOUND-1Y"], 0, True, 2, date(2026, 3, 26))
    ledger.pay(Decimal("61590.00"), date(2026, 6, 24))
    assert ledger.access_status(date(2026, 6, 24)) == "ACTIVE"


def test_unpaid_instalment_30_days_overdue_is_suspended(courses):
    ledger = ledger_for(courses["FOUND-1Y"], 0, False, 2, date(2026, 3, 26))
    assert ledger.access_status(date(2026, 5, 25)) == "ACTIVE"
    assert ledger.access_status(date(2026, 6, 24)) == "SUSPENDED"


def test_late_fee_accrues_on_unpaid_instalment_up_to_cap(courses):
    ledger = ledger_for(courses["FOUND-1Y"], 0, False, 2, date(2026, 3, 26))
    second = ledger.items[1]
    assert second.late_fee_on(date(2026, 6, 4)) == Decimal("0.00")
    assert second.late_fee_on(date(2026, 6, 14)) == Decimal("1000.00")
    assert second.late_fee_on(date(2026, 7, 31)) == Decimal("3000.00")


def test_payment_goes_to_earliest_unsettled_instalment_matches_enr_0017(courses):
    ledger = ledger_for(courses["NEET-1Y"], 0, False, 4, date(2026, 3, 27))
    ledger.pay(Decimal("50740.00"), date(2026, 5, 23))
    ledger.pay(Decimal("50740.00"), date(2026, 7, 20))
    assert [i.settled_on for i in ledger.items] == [
        date(2026, 3, 27), date(2026, 5, 23), date(2026, 7, 20), None,
    ]
    assert ledger.items[2].late_fee_charged == Decimal("0.00")


def test_late_payment_within_waiver_plan_includes_late_fee_matches_enr_0044(courses):
    ledger = ledger_for(courses["JEE-2Y"], 50, False, 4, date(2026, 3, 30))
    ledger.pay(Decimal("41890.00"), date(2026, 5, 26))
    ledger.pay(Decimal("42890.00"), date(2026, 8, 17))
    third = ledger.items[2]
    assert third.paid == Decimal("42890.00")
    assert third.late_fee_charged == Decimal("1000.00")
    assert third.settled_on == date(2026, 8, 17)


def test_overpayment_flows_to_next_instalment(courses):
    ledger = ledger_for(courses["NEET-1Y"], 0, False, 4, date(2026, 3, 27))
    ledger.pay(Decimal("101480.00"), date(2026, 5, 20))
    assert ledger.settled_count() == 3


def test_partial_payment_does_not_settle(courses):
    ledger = ledger_for(courses["FOUND-1Y"], 0, False, 2, date(2026, 3, 26))
    ledger.pay(Decimal("10000.00"), date(2026, 5, 1))
    assert ledger.items[1].settled_on is None
    assert ledger.items[1].paid == Decimal("10000.00")
    assert ledger.balance_on(date(2026, 5, 1)) == Decimal("54900.00")