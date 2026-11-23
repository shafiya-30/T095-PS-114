from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.engine import Engine
from src.events.parser import parse_commands, parse_lines

DATA = Path(__file__).resolve().parent.parent / "data"

GOOD_ENROL = "ENROL|ENR-1|STD-0020|2026-03-26|NEET-1Y|CTR-03|KANNADA|EVENING|1"


def run(lines):
    engine = Engine(DATA)
    engine.run(parse_lines(lines))
    return engine


def reasons(engine):
    return [e["reason"] for e in engine.errors]


@pytest.mark.parametrize(
    "line,reason",
    [
        ("ENROL|ENR-1|STD-9999|2026-03-26|NEET-1Y|CTR-03|KANNADA|EVENING|1", "UNKNOWN_STUDENT"),
        ("ENROL|ENR-1|STD-0020|2026-03-26|MBA-1Y|CTR-03|KANNADA|EVENING|1", "UNKNOWN_COURSE"),
        ("ENROL|ENR-1|STD-0020|2026-03-26|NEET-1Y|CTR-99|KANNADA|EVENING|1", "UNKNOWN_CENTRE"),
        ("ENROL|ENR-1|STD-0020|2026-03-26|NEET-1Y|CTR-03|FRENCH|EVENING|1", "INVALID_MEDIUM"),
        ("ENROL|ENR-1|STD-0020|2026-03-26|NEET-1Y|CTR-03|KANNADA|NIGHT|1", "INVALID_TIMING"),
        ("ENROL|ENR-1|STD-0020|2026-03-26|NEET-1Y|CTR-03|KANNADA|EVENING|3", "INVALID_PLAN"),
        ("ENROL|ENR-1|STD-0020|2026-03-26|NEET-1Y|CTR-03|KANNADA|EVENING|two", "INVALID_PLAN"),
        ("ENROL|ENR-1|STD-0020|2026-13-45|NEET-1Y|CTR-03|KANNADA|EVENING|1", "INVALID_DATE"),
        ("ENROL|ENR-1|STD-0020|-|NEET-1Y|CTR-03|KANNADA|EVENING|1", "INVALID_DATE"),
        ("ENROL|ENR-1", "WRONG_ARGUMENT_COUNT"),
        ("FLY|ENR-1", "UNKNOWN_COMMAND"),
        ("PUBLISH_RESULT|SCH-99|2026-03-25", "UNKNOWN_TEST"),
        ("PRINT_SCORES|SCH-01", "RESULT_NOT_PUBLISHED"),
        ("PRINT_ALLOCATION|BAT-99", "UNKNOWN_BATCH"),
        ("VIABILITY_CHECK|BAT-99|2026-04-01", "UNKNOWN_BATCH"),
        ("PAYMENT|PAY-1|ENR-404|2026-05-01|100.00|UPI", "UNKNOWN_ENROLMENT"),
        ("DROPOUT|ENR-404|2026-05-01|false", "UNKNOWN_ENROLMENT"),
        ("TRANSFER|ENR-404|2026-05-01|BAT-14", "UNKNOWN_ENROLMENT"),
        ("UPGRADE|ENR-404|2026-05-01|JEE-2Y|BAT-13", "UNKNOWN_ENROLMENT"),
        ("PRINT_FEE_STATEMENT|ENR-404|2026-07-31", "UNKNOWN_ENROLMENT"),
        ("PRINT_REFUND_ORDERS|2026-07-31|2026-04-01", "INVALID_DATE_RANGE"),
        ("PRINT_WAITLIST|not-a-date", "INVALID_DATE"),
    ],
)
def test_bad_command_gives_a_clear_error_and_does_not_crash(line, reason):
    engine = run([line])
    assert reasons(engine) == [reason]
    assert engine.errors[0]["line"] == 1
    assert engine.enrolments == {}


def test_processing_continues_after_an_invalid_command():
    engine = run(["ENROL|ENR-0|STD-9999|2026-03-26|NEET-1Y|CTR-03|KANNADA|EVENING|1", GOOD_ENROL])
    assert reasons(engine) == ["UNKNOWN_STUDENT"]
    assert list(engine.enrolments) == ["ENR-1"]


def test_duplicate_enrolment_id_is_rejected():
    engine = run([GOOD_ENROL, GOOD_ENROL])
    assert reasons(engine) == ["DUPLICATE_ENROLMENT"]
    assert len(engine.enrolments) == 1


@pytest.mark.parametrize("amount", ["abc", "-5", "0", "NaN", "-"])
def test_invalid_payment_amount_is_rejected(amount):
    engine = run([GOOD_ENROL, f"PAYMENT|PAY-1|ENR-1|2026-05-01|{amount}|UPI"])
    assert reasons(engine) == ["INVALID_AMOUNT"]


def test_duplicate_payment_id_is_rejected():
    engine = run(
        [
            "ENROL|ENR-1|STD-0020|2026-03-26|NEET-1Y|CTR-03|KANNADA|EVENING|2",
            "PAYMENT|PAY-1|ENR-1|2026-05-01|10.00|UPI",
            "PAYMENT|PAY-1|ENR-1|2026-05-02|10.00|UPI",
        ]
    )
    assert reasons(engine) == ["DUPLICATE_PAYMENT"]


def test_dropped_enrolment_cannot_pay_transfer_or_drop_again():
    engine = run(
        [
            GOOD_ENROL,
            "DROPOUT|ENR-1|2026-04-01|false",
            "PAYMENT|PAY-1|ENR-1|2026-05-01|100.00|UPI",
            "TRANSFER|ENR-1|2026-05-01|BAT-16",
            "DROPOUT|ENR-1|2026-05-02|false",
        ]
    )
    assert reasons(engine) == ["ALREADY_DROPPED"] * 3
    assert len(engine.refund_orders) == 1


def test_upgrade_to_a_batch_of_another_course_is_rejected():
    engine = run([GOOD_ENROL, "UPGRADE|ENR-1|2026-04-01|NEET-2Y|BAT-16"])
    assert reasons(engine) == ["BATCH_COURSE_MISMATCH"]
    assert engine.enrolments["ENR-1"].course_id == "NEET-1Y"


def test_transfer_to_unknown_batch_leaves_the_student_in_place():
    engine = run([GOOD_ENROL, "TRANSFER|ENR-1|2026-04-01|BAT-99"])
    assert reasons(engine) == ["UNKNOWN_BATCH"]
    assert engine.enrolments["ENR-1"].batch_id == "BAT-16"


def full_batch_lines():
    return [
        "ENROL|ENR-A|STD-0001|2026-03-26|NEET-1Y|CTR-03|ENGLISH|MORNING|1",
        "ENROL|ENR-B|STD-0002|2026-03-27|NEET-1Y|CTR-03|ENGLISH|MORNING|1",
    ]


def test_second_student_is_waitlisted_when_the_last_seat_is_taken():
    engine = run(full_batch_lines())
    assert engine.enrolments["ENR-A"].batch_id == "BAT-15"
    assert engine.enrolments["ENR-B"].status == "WAITLISTED"
    assert engine.errors == []


def test_dropout_gives_the_freed_seat_to_the_first_waitlisted_student():
    engine = run(full_batch_lines() + ["DROPOUT|ENR-A|2026-04-20|false"])
    b = engine.enrolments["ENR-B"]
    assert b.status == "ALLOCATED"
    assert b.batch_id == "BAT-15"
    assert engine.waitlist.entries == []
    assert engine.batches["BAT-15"].confirmed == 60
    assert engine.promotions == [{"enrol_id": "ENR-B", "batch_id": "BAT-15", "date": date(2026, 4, 20)}]
    assert engine.ledgers["ENR-B"].items[0].settled_on == date(2026, 4, 20)


def test_transfer_out_also_frees_a_seat_for_the_waitlist():
    engine = run(full_batch_lines() + ["TRANSFER|ENR-A|2026-04-10|BAT-16"])
    assert engine.enrolments["ENR-A"].batch_id == "BAT-16"
    assert engine.enrolments["ENR-B"].status == "ALLOCATED"
    assert engine.enrolments["ENR-B"].batch_id == "BAT-15"


def test_waitlisted_student_can_drop_out_without_a_refund():
    engine = run(full_batch_lines() + ["DROPOUT|ENR-B|2026-04-01|false"])
    assert engine.enrolments["ENR-B"].status == "DROPPED"
    assert engine.waitlist.entries == []
    assert engine.refund_orders == []


def test_payment_for_a_waitlisted_student_is_rejected():
    engine = run(full_batch_lines() + ["PAYMENT|PAY-1|ENR-B|2026-04-01|100.00|UPI"])
    assert reasons(engine) == ["NOT_SEATED"]


def test_plan_4_is_refused_after_two_suspensions():
    engine = Engine(DATA)
    engine.execute(next(parse_lines(["ENROL|ENR-1|STD-0020|2026-03-27|NEET-1Y|CTR-03|KANNADA|EVENING|4"])))
    ledger = engine.ledgers["ENR-1"]
    paid_on = date(2026, 7, 10)
    owed = ledger.items[1].owed_on(paid_on)
    engine.execute(next(parse_lines([f"PAYMENT|PAY-1|ENR-1|{paid_on}|{owed}|NEFT"])))
    assert engine.suspension_count("STD-0020", date(2026, 7, 31)) == 1
    assert engine.suspension_count("STD-0020", date(2026, 9, 30)) == 2
    engine.run(
        parse_lines(
            [
                "ENROL|ENR-2|STD-0020|2026-09-30|NEET-1Y|CTR-03|KANNADA|EVENING|4",
                "ENROL|ENR-3|STD-0020|2026-09-30|NEET-1Y|CTR-03|KANNADA|EVENING|2",
            ]
        )
    )
    assert reasons(engine) == ["PLAN_4_NOT_AVAILABLE"]
    assert "ENR-2" not in engine.enrolments
    assert engine.enrolments["ENR-3"].plan == 2


def test_plan_4_is_allowed_with_one_suspension():
    engine = Engine(DATA)
    engine.execute(next(parse_lines(["ENROL|ENR-1|STD-0020|2026-03-27|NEET-1Y|CTR-03|KANNADA|EVENING|4"])))
    engine.execute(next(parse_lines(["ENROL|ENR-2|STD-0020|2026-07-31|NEET-1Y|CTR-03|KANNADA|EVENING|4"])))
    assert engine.suspension_count("STD-0020", date(2026, 7, 31)) == 1
    assert engine.errors == []


@pytest.mark.skipif(not (DATA / "commands.txt").exists(), reason="sample data not present")
def test_sample_pack_runs_with_no_errors_and_no_promotions():
    engine = Engine(DATA)
    engine.run(parse_commands(DATA / "commands.txt"))
    assert engine.errors == []
    assert engine.promotions == []