from decimal import Decimal

from src.billing.referral import referral_credit


def test_credit_when_second_instalment_is_paid_matches_enr_0005():
    assert referral_credit(1, 2) == Decimal("5000.00")


def test_no_credit_for_first_instalment():
    assert referral_credit(0, 1) == Decimal("0.00")


def test_credit_only_once():
    assert referral_credit(2, 3) == Decimal("0.00")
    assert referral_credit(3, 4) == Decimal("0.00")


def test_paying_two_instalments_at_once_gives_one_credit():
    assert referral_credit(0, 2) == Decimal("5000.00")


def test_single_instalment_plan_never_earns_credit():
    assert referral_credit(0, 1) == Decimal("0.00")
    assert referral_credit(1, 1) == Decimal("0.00")