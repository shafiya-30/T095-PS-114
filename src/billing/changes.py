from dataclasses import dataclass
from decimal import Decimal

from src.billing.fees import compute_fee, money

ZERO = Decimal("0.00")
TRANSFER_FEE = Decimal("2500.00")
DOWNGRADE_CHARGE_PCT = 10


@dataclass(frozen=True)
class Change:
    allowed: bool
    amount: Decimal
    reason: str


def evaluate_transfer(source, target, free_transfers_used):
    if target.course_id != source.course_id:
        return Change(False, ZERO, "COURSE_MISMATCH")
    if target.seats_left <= 0:
        return Change(False, ZERO, "BATCH_FULL")
    if target.centre_id != source.centre_id:
        return Change(True, TRANSFER_FEE, "DIFFERENT_CENTRE")
    if free_transfers_used == 0:
        return Change(True, ZERO, "FREE_TRANSFER")
    return Change(True, TRANSFER_FEE, "REPEAT_TRANSFER")


def evaluate_course_change(
    old_course, new_course, current_batch, new_batch, change_date, waiver_pct, has_sibling, plan
):
    if new_batch.seats_left <= 0:
        return Change(False, ZERO, "BATCH_FULL")
    old_fee = compute_fee(old_course, waiver_pct, has_sibling, plan)
    new_fee = compute_fee(new_course, waiver_pct, has_sibling, plan)
    difference = new_fee.total - old_fee.total
    if new_course.tuition_fee >= old_course.tuition_fee:
        return Change(True, difference, "UPGRADE")
    if change_date >= current_batch.start_date:
        return Change(False, ZERO, "DOWNGRADE_AFTER_START")
    return Change(True, money(-difference * DOWNGRADE_CHARGE_PCT / 100), "DOWNGRADE")