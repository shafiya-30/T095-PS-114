import csv
from datetime import date
from pathlib import Path

import pytest

from src.engine import ALLOCATION_COLUMNS, Engine
from src.events.parser import parse_commands

DATA = Path(__file__).resolve().parent.parent / "data"
LAST_LINE = 198

pytestmark = pytest.mark.skipif(
    not (DATA / "commands.txt").exists(), reason="sample data not present"
)


@pytest.fixture(scope="module")
def engine():
    engine = Engine(DATA)
    engine.run([c for c in parse_commands(DATA / "commands.txt") if c.line_no <= LAST_LINE])
    return engine


def rows_for(engine, batch_id):
    return [r for r in engine.allocation_rows if r["batch_id"] == batch_id]


def test_batch_with_exactly_20_confirmed_is_not_merged(engine):
    rows = rows_for(engine, "BAT-14")
    assert {r["enrol_id"] for r in rows} == {
        "ENR-0062", "ENR-0089", "ENR-0125", "ENR-0141", "ENR-0143", "ENR-0147",
    }
    assert {r["status"] for r in rows} == {"ALLOCATED"}


def test_batch_with_19_confirmed_is_merged_into_bat_10(engine):
    rows = rows_for(engine, "BAT-11")
    assert {r["enrol_id"] for r in rows} == {
        "ENR-0042", "ENR-0073", "ENR-0102", "ENR-0132", "ENR-0142", "ENR-0144",
    }
    assert {r["status"] for r in rows} == {"MERGED"}
    assert engine.batches["BAT-11"].confirmed == 0


def test_merged_student_keeps_notice_date_and_new_batch(engine):
    e = engine.enrolments["ENR-0042"]
    assert e.batch_id == "BAT-10"
    assert e.merged_from == "BAT-11"
    assert e.merge_notice == date(2026, 5, 11)


def test_full_star_batch_lists_its_two_late_students(engine):
    rows = {r["enrol_id"]: r for r in rows_for(engine, "BAT-07")}
    assert "ENR-0016" in rows and "ENR-0027" in rows
    assert int(rows["ENR-0016"]["waiver_pct"]) >= 50
    assert "ENR-0045" not in rows


def test_waitlisted_student_is_in_no_allocation_list(engine):
    assert "ENR-0069" in {r["enrol_id"] for r in rows_for(engine, "BAT-15")}
    assert all(r["enrol_id"] != "ENR-0080" for r in engine.allocation_rows)


def test_allocations_file_has_readme_columns(engine, tmp_path):
    engine.write_outputs(tmp_path)
    with open(tmp_path / "allocations.csv", newline="") as f:
        reader = csv.DictReader(f)
        assert tuple(reader.fieldnames) == ALLOCATION_COLUMNS
        assert len(list(reader)) == len(engine.allocation_rows)