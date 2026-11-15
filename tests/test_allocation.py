from datetime import date
from pathlib import Path

import pytest

from src.allocation.allocation import choose_batch, seat_student
from src.allocation.batches import Batch, load_batches

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def batches():
    return load_batches(DATA / "batches.csv")


def batch(batch_id, batch_type, start, confirmed):
    return Batch(batch_id, "JEE-2Y", "CTR-01", "ENGLISH", "MORNING", batch_type,
                 date.fromisoformat(start), 60, confirmed)


def pick(batches, waiver, course="JEE-2Y", centre="CTR-02", medium="ENGLISH", timing="MORNING"):
    return choose_batch(batches, course, centre, medium, timing, waiver)


def test_loader_reads_all_batches(batches):
    assert len(batches) == 18
    assert batches["BAT-07"].seats_left == 2
    assert batches["BAT-07"].is_star


def test_waiver_50_or_more_prefers_star(batches):
    assert pick(batches, 75, centre="CTR-01").batch_id == "BAT-01"
    assert pick(batches, 50, centre="CTR-01").batch_id == "BAT-01"


def test_waiver_under_50_never_gets_star(batches):
    assert pick(batches, 25, centre="CTR-01", timing="MORNING") is None
    assert pick(batches, 25, centre="CTR-02").batch_id == "BAT-08"


def test_star_full_for_75_waiver_falls_to_regular(batches):
    seat_student(pick(batches, 90), "A")
    seat_student(pick(batches, 50), "B")
    assert batches["BAT-07"].seats_left == 0
    assert pick(batches, 75).batch_id == "BAT-08"


def test_regular_batches_fill_in_earliest_start_order():
    early = batch("B-EARLY", "REGULAR", "2026-04-20", 10)
    late = batch("B-LATE", "REGULAR", "2026-05-20", 10)
    both = {"B-LATE": late, "B-EARLY": early}
    assert choose_batch(both, "JEE-2Y", "CTR-01", "ENGLISH", "MORNING", 0) is early
    early.confirmed = 60
    assert choose_batch(both, "JEE-2Y", "CTR-01", "ENGLISH", "MORNING", 0) is late


def test_no_matching_batch_returns_none(batches):
    assert pick(batches, 0, course="NEET-2Y", centre="CTR-02") is None


def test_full_batch_returns_none_when_no_alternative(batches):
    assert pick(batches, 0, course="NEET-1Y", centre="CTR-03", timing="MORNING").batch_id == "BAT-15"
    seat_student(batches["BAT-15"], "ENR-0069")
    assert pick(batches, 0, course="NEET-1Y", centre="CTR-03", timing="MORNING") is None


def test_seat_student_updates_count_and_roster(batches):
    b = batches["BAT-01"]
    seat_student(b, "ENR-0009")
    assert b.confirmed == 22
    assert b.students == ["ENR-0009"]