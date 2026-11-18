import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.engine import REFUND_COLUMNS, WAITLIST_COLUMNS, Engine
from src.events.parser import parse_commands

DATA = Path(__file__).resolve().parent.parent / "data"

pytestmark = pytest.mark.skipif(
    not (DATA / "commands.txt").exists(), reason="sample data not present"
)


@pytest.fixture(scope="module")
def engine():
    engine = Engine(DATA)
    engine.run(parse_commands(DATA / "commands.txt"))
    return engine


def order(engine, enrol_id):
    return next(o for o in engine.refund_orders if o.enrol_id == enrol_id)


def test_every_dropout_produces_one_refund_order(engine):
    assert len(engine.refund_orders) == 9
    assert len({o.enrol_id for o in engine.refund_orders}) == 9


def test_day_15_refund_includes_unopened_material_matches_enr_0049(engine):
    o = order(engine, "ENR-0049")
    assert (o.days_from_start, o.refund_pct) == (15, 75)
    assert o.material_refund == Decimal("12000.00")


def test_day_16_refund_drops_to_50_and_material_not_refunded_matches_enr_0012(engine):
    o = order(engine, "ENR-0012")
    assert (o.days_from_start, o.refund_pct) == (16, 50)
    assert o.material_refund == Decimal("0.00")


def test_dropout_before_start_refunds_90_percent_matches_enr_0038(engine):
    o = order(engine, "ENR-0038")
    assert o.refund_pct == 90
    assert o.days_from_start < 0


def test_after_60_days_refund_is_nil_matches_enr_0035(engine):
    o = order(engine, "ENR-0035")
    assert (o.days_from_start, o.refund_pct) == (63, 0)
    assert o.total_refund == Decimal("0.00")


def test_31_to_60_day_band_matches_enr_0006_and_enr_0004(engine):
    assert (order(engine, "ENR-0006").days_from_start, order(engine, "ENR-0006").refund_pct) == (33, 25)
    assert (order(engine, "ENR-0004").days_from_start, order(engine, "ENR-0004").refund_pct) == (40, 25)


def test_merged_student_gets_full_refund_within_7_days_matches_enr_0042(engine):
    o = order(engine, "ENR-0042")
    assert o.refund_pct == 100
    assert o.waiver_forfeited is False


def test_star_dropout_within_15_days_forfeits_waiver_matches_enr_0019(engine):
    o = order(engine, "ENR-0019")
    assert (o.days_from_start, o.refund_pct) == (8, 75)
    assert o.waiver_forfeited is True
    assert engine.waiver_forfeitures["STD-0129"] == date(2026, 4, 28)


def test_refund_clock_counts_from_original_batch_matches_enr_0020(engine):
    o = order(engine, "ENR-0020")
    assert (o.days_from_start, o.refund_pct) == (23, 50)


def test_total_is_tuition_plus_material_plus_gst(engine):
    for o in engine.refund_orders:
        assert o.total_refund == o.tuition_refund + o.material_refund + o.gst_refund


def test_dropped_students_are_marked_dropped(engine):
    for o in engine.refund_orders:
        assert engine.enrolments[o.enrol_id].status == "DROPPED"


def test_printed_refund_orders_are_sorted_by_request_date(engine):
    dates = [r["request_date"] for r in engine.refund_rows]
    assert len(dates) == 9
    assert dates == sorted(dates)


def test_refund_file_has_readme_columns(engine, tmp_path):
    engine.write_outputs(tmp_path)
    with open(tmp_path / "refund_orders.csv", newline="") as f:
        reader = csv.DictReader(f)
        assert tuple(reader.fieldnames) == REFUND_COLUMNS
        assert len(list(reader)) == 9


def test_waitlist_file_lists_the_waiting_student(engine, tmp_path):
    engine.write_outputs(tmp_path)
    with open(tmp_path / "waitlist.csv", newline="") as f:
        reader = csv.DictReader(f)
        assert tuple(reader.fieldnames) == WAITLIST_COLUMNS
        rows = list(reader)
    assert [(r["enrol_id"], r["position"], r["as_of_date"]) for r in rows] == [
        ("ENR-0080", "1", "2026-07-31")
    ]