from pathlib import Path

import pytest

from src.engine import Engine
from src.events.parser import parse_commands

DATA = Path(__file__).resolve().parent.parent / "data"
LAST_ENROL_LINE = 163

pytestmark = pytest.mark.skipif(
    not (DATA / "commands.txt").exists(), reason="sample data not present"
)


@pytest.fixture(scope="module")
def engine():
    engine = Engine(DATA)
    commands = [
        c for c in parse_commands(DATA / "commands.txt") if c.line_no <= LAST_ENROL_LINE
    ]
    engine.run(commands)
    return engine


def test_all_150_enrolments_are_recorded(engine):
    assert len(engine.enrolments) == 150


def test_waiver_kept_on_day_15_goes_to_star_batch(engine):
    e = engine.enrolments["ENR-0136"]
    assert e.waiver_pct == 50
    assert e.batch_id == "BAT-04"


def test_waiver_forfeited_on_day_16(engine):
    assert engine.enrolments["ENR-0140"].waiver_pct == 0


def test_star_batch_fills_then_75_waiver_student_goes_to_regular(engine):
    assert engine.enrolments["ENR-0016"].batch_id == "BAT-07"
    assert engine.enrolments["ENR-0027"].batch_id == "BAT-07"
    assert engine.batches["BAT-07"].confirmed == 60
    e = engine.enrolments["ENR-0045"]
    assert e.waiver_pct == 75
    assert e.batch_id == "BAT-08"


def test_star_goes_to_star_and_capped_waiver_to_regular(engine):
    assert engine.enrolments["ENR-0009"].batch_id == "BAT-01"
    assert engine.enrolments["ENR-0009"].waiver_pct == 75
    assert engine.enrolments["ENR-0012"].batch_id == "BAT-02"
    assert engine.enrolments["ENR-0012"].waiver_pct == 25


def test_last_seat_taken_then_next_student_is_waitlisted(engine):
    assert engine.enrolments["ENR-0069"].status == "ALLOCATED"
    assert engine.enrolments["ENR-0069"].batch_id == "BAT-15"
    assert engine.batches["BAT-15"].confirmed == 60
    assert engine.enrolments["ENR-0080"].status == "WAITLISTED"
    assert engine.enrolments["ENR-0080"].batch_id is None
    assert "ENR-0080" in [w.enrol_id for w in engine.waitlist.entries]


def test_batch_counts_before_viability_checks(engine):
    assert engine.batches["BAT-14"].confirmed == 20
    assert engine.batches["BAT-11"].confirmed == 19


def test_sibling_flag_and_90_percent_waiver(engine):
    e = engine.enrolments["ENR-0008"]
    assert e.waiver_pct == 90
    assert e.has_sibling is True


def test_retest_gives_better_waiver(engine):
    assert engine.enrolments["ENR-0101"].waiver_pct == 90
    assert engine.enrolments["ENR-0113"].waiver_pct == 25