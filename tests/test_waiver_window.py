from datetime import date

from src.scoring.scoring import effective_waiver

FIRST = date(2026, 3, 25)
RETEST = date(2026, 4, 2)


def test_waiver_kept_on_day_15_matches_enr_0136():
    assert effective_waiver([(50, FIRST)], date(2026, 4, 9)) == 50


def test_waiver_forfeited_on_day_16_matches_enr_0140():
    assert effective_waiver([(50, FIRST)], date(2026, 4, 10)) == 0


def test_no_attempts_means_no_waiver():
    assert effective_waiver([], date(2026, 4, 1)) == 0


def test_retest_gives_the_better_waiver():
    attempts = [(25, FIRST), (90, RETEST)]
    assert effective_waiver(attempts, date(2026, 4, 5)) == 90


def test_better_of_two_even_when_retest_is_lower():
    attempts = [(25, FIRST), (0, RETEST)]
    assert effective_waiver(attempts, date(2026, 4, 5)) == 25


def test_retest_window_keeps_waiver_after_first_window_lapses():
    attempts = [(50, FIRST), (25, RETEST)]
    assert effective_waiver(attempts, date(2026, 4, 10)) == 25


def test_result_not_yet_published_is_ignored():
    assert effective_waiver([(90, RETEST)], date(2026, 4, 1)) == 0