import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.engine import STATEMENT_COLUMNS, Engine
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


def rows_for(engine, enrol_id):
    return [r for r in engine.statement_rows if r["enrol_id"] == enrol_id]


def test_every_payment_settles_exactly_one_instalment():
    engine = Engine(DATA)
    for command in parse_commands(DATA / "commands.txt"):
        if command.name == "PAYMENT":
            ledger = engine.ledgers.get(command.args[1])
            assert ledger is not None, command.args[0]
            before = ledger.settled_count()
            engine.execute(command)
            assert ledger.settled_count() == before + 1, command.args[0]
        else:
            engine.execute(command)


def test_payment_arriving_30_days_overdue_matches_enr_0001(engine):
    first, second = rows_for(engine, "ENR-0001")
    assert first["amount"] == Decimal("59590.00")
    assert second["due_date"] == date(2026, 5, 25)
    assert second["late_fee"] == Decimal("2000.00")
    assert second["paid"] == Decimal("61590.00")
    assert second["balance"] == Decimal("0.00")
    assert second["access_status"] == "ACTIVE"


def test_plan_2_instalments_match_pay_0001(engine):
    rows = rows_for(engine, "ENR-0013")
    assert [r["amount"] for r in rows] == [Decimal("64900.00")] * 2
    assert [r["paid"] for r in rows] == [Decimal("64900.00")] * 2


def test_plan_4_statement_shows_paid_and_unpaid_instalments_matches_enr_0017(engine):
    rows = rows_for(engine, "ENR-0017")
    assert len(rows) == 4
    assert [r["paid"] for r in rows] == [Decimal("50740.00")] * 3 + [Decimal("0.00")]
    last = rows[3]
    assert last["due_date"] == date(2026, 9, 23)
    assert last["balance"] == Decimal("50740.00")
    assert last["late_fee"] == Decimal("0.00")


def test_late_payment_after_the_statement_matches_enr_0044(engine):
    third = engine.ledgers["ENR-0044"].items[2]
    assert third.paid == Decimal("42890.00")
    assert third.late_fee_charged == Decimal("1000.00")


def test_payment_inside_grace_has_no_late_fee_matches_enr_0043(engine):
    third = engine.ledgers["ENR-0043"].items[2]
    assert third.paid == Decimal("50740.00")
    assert third.late_fee_charged == Decimal("0.00")


def test_referral_credit_after_second_instalment_matches_enr_0005(engine):
    assert engine.referral_credits["STD-0001"] >= Decimal("5000.00")


def test_waitlisted_student_has_no_statement(engine):
    assert rows_for(engine, "ENR-0080") == []
    assert rows_for(engine, "ENR-0001") != []


def test_statements_are_dated_with_the_request_date(engine):
    assert {r["as_of_date"] for r in engine.statement_rows} == {date(2026, 7, 31)}


def test_statement_file_has_readme_columns(engine, tmp_path):
    engine.write_outputs(tmp_path)
    with open(tmp_path / "fee_statements.csv", newline="") as f:
        reader = csv.DictReader(f)
        assert tuple(reader.fieldnames) == STATEMENT_COLUMNS
        assert len(list(reader)) == len(engine.statement_rows)