from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.engine import Engine
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


def charge(engine, enrol_id):
    return engine.enrolments[enrol_id].extra_charges[0]


def test_free_same_centre_transfer_matches_enr_0057(engine):
    e = engine.enrolments["ENR-0057"]
    assert e.batch_id == "BAT-14"
    assert e.status == "TRANSFERRED"
    assert e.free_transfers_used == 1
    assert charge(engine, "ENR-0057")[1:] == ("FREE_TRANSFER", Decimal("0.00"))
    assert "ENR-0057" in engine.batches["BAT-14"].students
    assert "ENR-0057" not in engine.batches["BAT-13"].students


def test_transfer_to_other_centre_costs_2500_matches_enr_0020(engine):
    assert charge(engine, "ENR-0020")[1:] == ("DIFFERENT_CENTRE", Decimal("2500.00"))
    assert engine.enrolments["ENR-0020"].batch_id == "BAT-08"


def test_transfer_keeps_the_original_batch_for_the_refund_clock(engine):
    assert engine.enrolments["ENR-0020"].original_batch_id == "BAT-02"
    assert engine.enrolments["ENR-0057"].original_batch_id == "BAT-13"


def test_upgrade_bills_difference_and_keeps_waiver_matches_enr_0026(engine):
    e = engine.enrolments["ENR-0026"]
    assert e.waiver_pct == 75
    assert e.course_id == "NEET-2Y"
    assert e.batch_id == "BAT-05"
    assert charge(engine, "ENR-0026")[1:] == ("UPGRADE", Decimal("30827.50"))


def test_downgrade_before_batch_start_is_allowed_matches_enr_0040(engine):
    e = engine.enrolments["ENR-0040"]
    assert e.course_id == "JEE-1Y"
    assert e.batch_id == "BAT-03"
    reason, amount = charge(engine, "ENR-0040")[1:]
    assert reason == "DOWNGRADE"
    assert amount > Decimal("0.00")


def test_downgrade_after_batch_start_is_rejected_matches_enr_0059(engine):
    assert engine.rejections == [
        {"command": "UPGRADE", "enrol_id": "ENR-0059", "reason": "DOWNGRADE_AFTER_START"}
    ]
    e = engine.enrolments["ENR-0059"]
    assert e.course_id == "JEE-2Y"
    assert e.batch_id == "BAT-13"
    assert e.extra_charges == []


def test_transfer_does_not_change_instalment_dates(engine):
    e = engine.enrolments["ENR-0020"]
    assert engine.ledgers["ENR-0020"].items[0].instalment.due_date == e.enrol_date