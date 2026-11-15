from datetime import date
from decimal import Decimal

import pytest

from src.scoring.scoring import (
    better_waiver,
    mark,
    percentile,
    score_cohort,
    section_scores,
    waiver_for,
    waiver_valid,
)

KEY = ["A"] * 60


def response(student_id, answers):
    return {"student_id": student_id, "answers": answers}


def test_marking_scheme():
    assert mark("A", "A") == 4
    assert mark("B", "A") == -1
    assert mark("-", "A") == 0


def test_section_scores_split_by_question_range():
    answers = "A" * 20 + "B" * 20 + "-" * 20
    assert section_scores(answers, KEY) == {"PHY": 80, "CHE": -20, "APT": 0}


@pytest.mark.parametrize(
    "pct,expected",
    [
        ("100.00", 90),
        ("99.00", 90),
        ("98.99", 75),
        ("95.00", 75),
        ("94.99", 50),
        ("90.00", 50),
        ("89.99", 25),
        ("80.00", 25),
        ("79.99", 0),
    ],
)
def test_waiver_bands(pct, expected):
    assert waiver_for(Decimal(pct), True) == expected


def test_failed_section_caps_waiver_at_25():
    assert waiver_for(Decimal("97.78"), False) == 25
    assert waiver_for(Decimal("82.00"), False) == 25
    assert waiver_for(Decimal("70.00"), False) == 0


def test_percentile_exactly_95():
    totals = [158] * 171 + [200] * 9
    assert percentile(158, totals) == Decimal("95.00")
    assert waiver_for(percentile(158, totals), True) == 75


def test_percentile_ties_share_value():
    totals = [10, 20, 20, 30]
    assert percentile(20, totals) == Decimal("75.00")
    assert percentile(10, totals) == Decimal("25.00")
    assert percentile(30, totals) == Decimal("100.00")


def test_section_score_exactly_24_passes_cutoff():
    answers = ("A" * 6 + "-" * 14) * 3
    scores = score_cohort("T", [response("S1", answers)], KEY)
    assert scores[0].che == 24
    assert scores[0].cutoff_passed is True


def test_section_score_23_fails_cutoff():
    answers = ("A" * 6 + "-" * 14) * 2 + "A" * 6 + "B" + "-" * 13
    scores = score_cohort("T", [response("S1", answers)], KEY)
    assert scores[0].apt == 23
    assert scores[0].cutoff_passed is False
    assert scores[0].waiver_pct <= 25


def test_cohort_sorted_by_total_desc_then_student_id():
    strong = "A" * 60
    weak = "-" * 60
    scores = score_cohort(
        "T",
        [response("S3", weak), response("S2", strong), response("S1", strong)],
        KEY,
    )
    assert [s.student_id for s in scores] == ["S1", "S2", "S3"]


def test_better_of_two_waivers():
    assert better_waiver(25, 90) == 90
    assert better_waiver(25, 0) == 25


def test_enrolment_window_boundary():
    result = date(2026, 3, 25)
    assert waiver_valid(result, date(2026, 4, 9)) is True
    assert waiver_valid(result, date(2026, 4, 10)) is False