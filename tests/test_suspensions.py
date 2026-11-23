from datetime import date

from src.billing.suspensions import suspension_episodes

DUE = date(2026, 5, 25)
DAY_30 = date(2026, 6, 24)


def test_unpaid_before_day_30_is_not_a_suspension():
    assert suspension_episodes([(DUE, None)], date(2026, 6, 23)) == 0


def test_unpaid_on_day_30_is_a_suspension():
    assert suspension_episodes([(DUE, None)], DAY_30) == 1


def test_payment_on_day_30_is_not_a_suspension():
    assert suspension_episodes([(DUE, DAY_30)], date(2026, 7, 31)) == 0


def test_payment_on_day_31_was_a_suspension():
    assert suspension_episodes([(DUE, date(2026, 6, 25))], date(2026, 7, 31)) == 1


def test_payment_made_after_the_checked_date_still_counts_as_unpaid():
    assert suspension_episodes([(DUE, date(2026, 8, 20))], date(2026, 7, 31)) == 1


def test_two_overlapping_overdue_instalments_are_one_suspension():
    pairs = [(date(2026, 5, 25), None), (date(2026, 7, 24), None)]
    assert suspension_episodes(pairs, date(2026, 9, 30)) == 1


def test_late_payment_then_a_new_lapse_is_two_suspensions():
    pairs = [(date(2026, 5, 25), date(2026, 7, 10)), (date(2026, 7, 24), None)]
    assert suspension_episodes(pairs, date(2026, 9, 30)) == 2


def test_no_instalments_means_no_suspensions():
    assert suspension_episodes([], date(2026, 9, 30)) == 0