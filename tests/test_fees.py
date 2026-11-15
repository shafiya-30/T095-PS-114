from decimal import Decimal
from pathlib import Path

import pytest

from src.billing.fees import compute_fee, load_courses, total_discount_pct

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def courses():
    return load_courses(DATA / "courses.csv")


def test_courses_loaded(courses):
    assert len(courses) == 5
    assert courses["JEE-2Y"].tuition_fee == Decimal("240000.00")


def test_no_discount_plan_2_matches_pay_0001(courses):
    fee = compute_fee(courses["FOUND-1Y"], 0, False, 2)
    assert fee.total == Decimal("129800.00")
    assert fee.total / 2 == Decimal("64900.00")


def test_plan_4_adds_processing_fee_with_gst_matches_pay_0002(courses):
    fee = compute_fee(courses["NEET-1Y"], 0, False, 4)
    assert fee.processing_fee == Decimal("2000.00")
    assert fee.total == Decimal("202960.00")
    assert fee.total / 4 == Decimal("50740.00")


def test_waiver_applies_to_tuition_only_matches_pay_0005(courses):
    fee = compute_fee(courses["JEE-2Y"], 50, False, 4)
    assert fee.tuition == Decimal("120000.00")
    assert fee.material == Decimal("12000.00")
    assert fee.total / 4 == Decimal("41890.00")


def test_sibling_discount_matches_enr_0001(courses):
    fee = compute_fee(courses["FOUND-1Y"], 0, True, 2)
    assert fee.tuition == Decimal("81000.00")
    assert fee.total / 2 == Decimal("59590.00")


def test_waiver_25_matches_pay_0004(courses):
    fee = compute_fee(courses["NEET-1Y"], 25, False, 2)
    assert fee.total / 2 == Decimal("78175.00")


def test_waiver_90_plus_sibling_10_is_capped_at_90(courses):
    assert total_discount_pct(90, True) == 90
    fee = compute_fee(courses["JEE-2Y"], 90, True, 2)
    assert fee.discount_pct == 90
    assert fee.tuition == Decimal("24000.00")


def test_waiver_and_sibling_stack_below_cap():
    assert total_discount_pct(50, True) == 60
    assert total_discount_pct(25, False) == 25


def test_plan_1_gives_5_percent_off_tuition(courses):
    fee = compute_fee(courses["JEE-2Y"], 0, False, 1)
    assert fee.tuition == Decimal("228000.00")
    assert fee.total == Decimal("292640.00")


def test_plan_1_discount_applies_after_waiver(courses):
    fee = compute_fee(courses["JEE-2Y"], 50, False, 1)
    assert fee.tuition == Decimal("114000.00")