from decimal import Decimal

REFERRAL_CREDIT = Decimal("5000.00")
QUALIFYING_INSTALMENT = 2


def referral_credit(paid_before, paid_after):
    if paid_before < QUALIFYING_INSTALMENT <= paid_after:
        return REFERRAL_CREDIT
    return Decimal("0.00")