from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.allocation.allocation import seat_student
from src.allocation.batches import load_batches
from src.billing.changes import evaluate_course_change, evaluate_transfer
from src.billing.fees import load_courses

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def batches():
    return load_batches(DATA / "batches.csv")


@pytest.fixture
def courses():
    return load_courses(DATA / "courses.csv")


def test_first_same_centre_transfer_is_free_matches_enr_0057(batches):
    result = evaluate_transfer(batches["BAT-13"], batches["BAT-14"], 0)
    assert result.allowed is True
    assert result.amount == Decimal("0.00")


def test_different_centre_transfer_costs_2500_matches_enr_0020(batches):
    result = evaluate_transfer(batches["BAT-02"], batches["BAT-08"], 0)
    assert result.allowed is True
    assert result.amount == Decimal("2500.00")


def test_repeat_same_centre_transfer_is_charged(batches):
    result = evaluate_transfer(batches["BAT-13"], batches["BAT-14"], 1)
    assert result.amount == Decimal("2500.00")


def test_transfer_to_other_course_is_rejected(batches):
    result = evaluate_transfer(batches["BAT-13"], batches["BAT-04"], 0)
    assert result.allowed is False


def test_transfer_to_full_batch_is_rejected(batches):
    for i in range(2):
        seat_student(batches["BAT-07"], f"X{i}")
    result = evaluate_transfer(batches["BAT-08"], batches["BAT-07"], 0)
    assert result.allowed is False
    assert result.reason == "BATCH_FULL"


def test_upgrade_bills_difference_and_keeps_waiver_matches_enr_0026(batches, courses):
    result = evaluate_course_change(
        courses["NEET-1Y"], courses["NEET-2Y"], batches["BAT-04"], batches["BAT-05"],
        date(2026, 5, 2), 75, False, 2,
    )
    assert result.allowed is True
    assert result.reason == "UPGRADE"
    assert result.amount == Decimal("32450.00")


def test_upgrade_difference_is_smaller_with_a_waiver(batches, courses):
    args = (courses["NEET-1Y"], courses["NEET-2Y"], batches["BAT-04"], batches["BAT-05"], date(2026, 5, 2))
    no_waiver = evaluate_course_change(*args, 0, False, 2)
    with_waiver = evaluate_course_change(*args, 50, False, 2)
    assert no_waiver.amount == Decimal("129800.00")
    assert with_waiver.amount == Decimal("64900.00")


def test_downgrade_before_start_charges_10_percent_of_difference_matches_enr_0040(batches, courses):
    result = evaluate_course_change(
        courses["JEE-2Y"], courses["JEE-1Y"], batches["BAT-02"], batches["BAT-03"],
        date(2026, 4, 22), 0, False, 2,
    )
    assert result.allowed is True
    assert result.reason == "DOWNGRADE"
    assert result.amount == Decimal("11800.00")


def test_downgrade_after_start_is_rejected_matches_enr_0059(batches, courses):
    result = evaluate_course_change(
        courses["JEE-2Y"], courses["JEE-1Y"], batches["BAT-13"], batches["BAT-03"],
        date(2026, 5, 6), 0, False, 1,
    )
    assert result.allowed is False
    assert result.reason == "DOWNGRADE_AFTER_START"


def test_downgrade_on_start_day_is_rejected(batches, courses):
    result = evaluate_course_change(
        courses["JEE-2Y"], courses["JEE-1Y"], batches["BAT-02"], batches["BAT-03"],
        date(2026, 4, 27), 0, False, 2,
    )
    assert result.allowed is False


def test_change_into_full_batch_is_rejected(batches, courses):
    for i in range(30):
        seat_student(batches["BAT-05"], f"X{i}")
    result = evaluate_course_change(
        courses["NEET-1Y"], courses["NEET-2Y"], batches["BAT-04"], batches["BAT-05"],
        date(2026, 5, 2), 0, False, 2,
    )
    assert result.allowed is False