from datetime import date
from pathlib import Path

import pytest

from src.allocation.allocation import seat_student
from src.allocation.batches import Batch, load_batches
from src.allocation.viability import check_viability, is_viable, merge_target

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def batches():
    return load_batches(DATA / "batches.csv")


def fill(batch, count):
    for i in range(count):
        seat_student(batch, f"{batch.batch_id}-{i}")


def test_exactly_20_confirmed_is_viable(batches):
    fill(batches["BAT-14"], 6)
    assert batches["BAT-14"].confirmed == 20
    assert is_viable(batches["BAT-14"])
    assert check_viability(batches, "BAT-14") is None
    assert batches["BAT-14"].confirmed == 20


def test_19_confirmed_is_merged_into_nearest_same_course_batch(batches):
    fill(batches["BAT-11"], 6)
    assert batches["BAT-11"].confirmed == 19
    target, moved = check_viability(batches, "BAT-11")
    assert target.batch_id == "BAT-10"
    assert len(moved) == 6
    assert target.confirmed == 29 + 19
    assert batches["BAT-11"].confirmed == 0
    assert batches["BAT-11"].students == []


def test_merge_ignores_other_courses_even_if_closer(batches):
    assert merge_target(batches, batches["BAT-11"]).batch_id != "BAT-08"


def test_merge_stays_in_same_centre_and_medium(batches):
    target = merge_target(batches, batches["BAT-10"])
    assert target.batch_id == "BAT-09"
    assert target.centre_id == "CTR-02"
    assert target.medium == "ENGLISH"


def test_other_medium_is_not_a_merge_target(batches):
    assert merge_target(batches, batches["BAT-14"]) is None


def test_equal_distance_prefers_earlier_start():
    def make(batch_id, start):
        return Batch(batch_id, "C", "X", "ENGLISH", "MORNING", "REGULAR", date.fromisoformat(start), 60, 30)

    source = make("S", "2026-05-10")
    before = make("B", "2026-05-05")
    after = make("A", "2026-05-15")
    pool = {"S": source, "A": after, "B": before}
    assert merge_target(pool, source) is before


def test_no_candidate_leaves_batch_unmerged():
    only = Batch("S", "C", "X", "ENGLISH", "MORNING", "REGULAR", date(2026, 5, 10), 60, 5)
    assert check_viability({"S": only}, "S") is None
    assert only.confirmed == 5