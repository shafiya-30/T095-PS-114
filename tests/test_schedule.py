from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.billing.fees import compute_fee, load_courses
from src.billing.schedule import build_schedule, split_equal

DATA = Path(__file__).resolve().parent.parent / "data"
ENROL = date(2026, 3, 26)


@pytest.fixture
def courses():
    return load_courses(DATA / "courses.csv")


def test_split_equal_last_instalment_absorbs_rounding():
    assert split_equal(Decimal("100.00"), 3) == [
        Decimal("33.33"),
        Decimal("33.33"),
        Decimal("33.34"),
    ]


def test_plan_1_is_a_single_payment_on_enrol_date(courses):
    fee = compute_fee(courses["JEE-2Y"], 0, False, 1)
    schedule = build_schedule(fee, 1, ENROL)
    assert len(schedule) == 1
    assert schedule[0].due_date == ENROL
    assert schedule[0].amount == fee.total


def test_plan_2_due_dates_and_amounts_match_pay_0001(courses):
    fee = compute_fee(courses["FOUND-1Y"], 0, False, 2)
    schedule = build_schedule(fee, 2, ENROL)
    assert [i.due_date for i in schedule] == [date(2026, 3, 26), date(2026, 5, 25)]
    assert [i.amount for i in schedule] == [Decimal("64900.00")] * 2


def test_plan_4_due_dates_and_amounts_match_pay_0002(courses):
    fee = compute_fee(courses["NEET-1Y"], 0, False, 4)
    schedule = build_schedule(fee, 4, date(2026, 3, 27))
    assert [i.due_date for i in schedule] == [
        date(2026, 3, 27),
        date(2026, 5, 26),
        date(2026, 7, 25),
        date(2026, 9, 23),
    ]
    assert [i.amount for i in schedule] == [Decimal("50740.00")] * 4


def test_plan_4_processing_fee_is_split_across_instalments(courses):
    fee = compute_fee(courses["NEET-1Y"], 0, False, 4)
    schedule = build_schedule(fee, 4, ENROL)
    assert sum(i.processing_fee for i in schedule) == Decimal("2000.00")


def test_instalments_always_add_up_to_the_total(courses):
    for course in courses.values():
        for waiver in (0, 25, 50, 75, 90):
            for sibling in (False, True):
                for plan in (1, 2, 4):
                    fee = compute_fee(course, waiver, sibling, plan)
                    schedule = build_schedule(fee, plan, ENROL)
                    assert sum(i.amount for i in schedule) == fee.total
                    for i in schedule:
                        parts = i.tuition + i.material + i.exam_series + i.processing_fee + i.gst
                        assert parts == i.amount