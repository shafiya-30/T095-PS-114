from datetime import date
from decimal import Decimal

import pytest

from src.refunds.refunds import (
    compute_refund,
    days_from_start,
    material_refundable,
    merge_refund_eligible,
    refund_pct,
    waiver_forfeited,
)

START = date(2026, 4, 27)


def order(day_offset, tuition="240000.00", material="12000.00", unopened=True, star=False, merged=False):
    request = date.fromordinal(START.toordinal() + day_offset)
    return compute_refund(
        "ENR", request, START, Decimal(tuition), Decimal(material), Decimal("18"), unopened, star, merged
    )


def test_start_date_is_day_zero():
    assert days_from_start(START, START) == 0
    assert days_from_start(START, date(2026, 5, 12)) == 15
    assert days_from_start(START, date(2026, 4, 25)) == -2


@pytest.mark.parametrize(
    "days,expected",
    [
        (-10, 90),
        (-1, 90),
        (0, 75),
        (8, 75),
        (15, 75),
        (16, 50),
        (30, 50),
        (31, 25),
        (33, 25),
        (60, 25),
        (61, 0),
        (63, 0),
    ],
)
def test_refund_ladder(days, expected):
    assert refund_pct(days) == expected


def test_day_15_refund_with_unopened_material_matches_enr_0049():
    r = order(15)
    assert r.refund_pct == 75
    assert r.tuition_refund == Decimal("180000.00")
    assert r.material_refund == Decimal("12000.00")
    assert r.gst_refund == Decimal("34560.00")
    assert r.total_refund == Decimal("226560.00")


def test_day_16_drops_to_50_and_material_not_refundable_matches_enr_0012():
    r = order(16)
    assert r.refund_pct == 50
    assert r.tuition_refund == Decimal("120000.00")
    assert r.material_refund == Decimal("0.00")
    assert r.gst_refund == Decimal("21600.00")


def test_refund_percentage_applies_to_waiver_adjusted_tuition():
    r = order(8, tuition="120000.00")
    assert r.tuition_refund == Decimal("90000.00")


def test_refund_is_on_tuition_actually_paid_so_far():
    r = order(8, tuition="30000.00")
    assert r.tuition_refund == Decimal("22500.00")


def test_before_start_refunds_90_percent():
    r = order(-5, material="12000.00", unopened=False)
    assert r.refund_pct == 90
    assert r.tuition_refund == Decimal("216000.00")
    assert r.material_refund == Decimal("0.00")


def test_after_60_days_refund_is_nil():
    r = order(63)
    assert r.refund_pct == 0
    assert r.total_refund == Decimal("0.00")


def test_opened_material_is_not_refunded_even_inside_15_days():
    assert material_refundable(10, False) is False
    assert material_refundable(10, True) is True
    assert material_refundable(15, True) is True
    assert material_refundable(16, True) is False


def test_star_dropout_within_15_days_forfeits_waiver_matches_enr_0019():
    assert order(8, star=True).waiver_forfeited is True
    assert order(15, star=True).waiver_forfeited is True
    assert order(16, star=True).waiver_forfeited is False
    assert order(8, star=False).waiver_forfeited is False


def test_dropout_before_start_does_not_forfeit_waiver():
    assert waiver_forfeited(True, -3) is False


def test_merge_window_is_7_days_from_notice_matches_enr_0042():
    notice = date(2026, 5, 11)
    assert merge_refund_eligible(notice, date(2026, 5, 15)) is True
    assert merge_refund_eligible(notice, date(2026, 5, 18)) is True
    assert merge_refund_eligible(notice, date(2026, 5, 19)) is False
    assert merge_refund_eligible(notice, date(2026, 5, 10)) is False


def test_merged_student_gets_full_refund_without_forfeiture():
    r = order(40, star=True, merged=True, unopened=False)
    assert r.refund_pct == 100
    assert r.tuition_refund == Decimal("240000.00")
    assert r.material_refund == Decimal("12000.00")
    assert r.waiver_forfeited is False