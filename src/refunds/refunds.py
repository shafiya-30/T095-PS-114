from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.billing.fees import money

BEFORE_START_PCT = 90
LADDER = ((15, 75), (30, 50), (60, 25))
MATERIAL_WINDOW_DAYS = 15
STAR_FORFEIT_DAYS = 15
MERGE_WINDOW_DAYS = 7


@dataclass(frozen=True)
class RefundOrder:
    enrol_id: str
    request_date: date
    days_from_start: int
    refund_pct: int
    tuition_refund: Decimal
    material_refund: Decimal
    gst_refund: Decimal
    total_refund: Decimal
    waiver_forfeited: bool


def days_from_start(start_date, request_date):
    return (request_date - start_date).days


def refund_pct(days):
    if days < 0:
        return BEFORE_START_PCT
    for limit, pct in LADDER:
        if days <= limit:
            return pct
    return 0


def material_refundable(days, unopened):
    return unopened and days <= MATERIAL_WINDOW_DAYS


def waiver_forfeited(is_star_batch, days):
    return is_star_batch and 0 <= days <= STAR_FORFEIT_DAYS


def merge_refund_eligible(notice_date, request_date):
    return 0 <= (request_date - notice_date).days <= MERGE_WINDOW_DAYS


def compute_refund(
    enrol_id,
    request_date,
    start_date,
    tuition_paid,
    material_paid,
    gst_pct,
    material_unopened,
    is_star_batch,
    merge_full_refund=False,
):
    days = days_from_start(start_date, request_date)
    if merge_full_refund:
        pct = 100
        material = money(material_paid)
        forfeited = False
    else:
        pct = refund_pct(days)
        material = money(material_paid) if material_refundable(days, material_unopened) else Decimal("0.00")
        forfeited = waiver_forfeited(is_star_batch, days)
    tuition = money(tuition_paid * pct / 100)
    gst = money((tuition + material) * gst_pct / 100)
    return RefundOrder(
        enrol_id,
        request_date,
        days,
        pct,
        tuition,
        material,
        gst,
        tuition + material + gst,
        forfeited,
    )