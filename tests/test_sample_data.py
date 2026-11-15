from decimal import Decimal
from pathlib import Path

import pytest

from src.scoring.loader import load_answer_keys, load_responses
from src.scoring.scoring import score_cohort

DATA = Path(__file__).resolve().parent.parent / "data"

pytestmark = pytest.mark.skipif(
    not (DATA / "answer_key.csv").exists(), reason="sample data not present"
)


@pytest.fixture(scope="module")
def cohorts():
    keys = load_answer_keys(DATA / "answer_key.csv")
    responses = load_responses(DATA / "test_responses.csv")
    return {
        test: {s.student_id: s for s in score_cohort(test, responses[test], keys[test])}
        for test in responses
    }


def test_cohort_sizes(cohorts):
    assert len(cohorts["SCH-01"]) == 180
    assert len(cohorts["SCH-02"]) == 20


def test_percentile_exactly_95(cohorts):
    s = cohorts["SCH-01"]["STD-0009"]
    assert s.total == 158
    assert s.percentile == Decimal("95.00")
    assert s.waiver_pct == 75


def test_section_exactly_at_cutoff(cohorts):
    s = cohorts["SCH-01"]["STD-0164"]
    assert s.che == 24
    assert s.cutoff_passed is True
    assert s.waiver_pct == 75


def test_one_mark_under_cutoff_is_capped(cohorts):
    s = cohorts["SCH-01"]["STD-0026"]
    assert s.apt == 23
    assert s.percentile == Decimal("97.78")
    assert s.waiver_pct == 25


def test_tied_totals_share_percentile(cohorts):
    a = cohorts["SCH-01"]["STD-0070"]
    b = cohorts["SCH-01"]["STD-0133"]
    assert a.total == b.total == 153
    assert a.percentile == b.percentile == Decimal("93.33")


def test_topper_gets_90(cohorts):
    s = cohorts["SCH-01"]["STD-0153"]
    assert s.percentile == Decimal("100.00")
    assert s.waiver_pct == 90


def test_retest_waivers(cohorts):
    assert cohorts["SCH-02"]["STD-0096"].waiver_pct == 90
    assert cohorts["SCH-01"]["STD-0096"].waiver_pct == 25
    assert cohorts["SCH-02"]["STD-0073"].waiver_pct == 0
    assert cohorts["SCH-01"]["STD-0073"].waiver_pct == 25