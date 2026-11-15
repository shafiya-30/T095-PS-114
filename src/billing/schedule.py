from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from src.billing.fees import money

PLAN_OFFSETS = {1: (0,), 2: (0, 60), 4: (0, 60, 120, 180)}


@dataclass(frozen=True)
class Instalment:
    no: int
    due_date: date
    tuition: Decimal
    material: Decimal
    exam_series: Decimal
    processing_fee: Decimal
    gst: Decimal
    amount: Decimal


def split_equal(amount, parts):
    share = money(amount / parts)
    return [share] * (parts - 1) + [amount - share * (parts - 1)]


def build_schedule(fee, plan, enrol_date):
    offsets = PLAN_OFFSETS[plan]
    parts = len(offsets)
    tuition = split_equal(fee.tuition, parts)
    material = split_equal(fee.material, parts)
    exam_series = split_equal(fee.exam_series, parts)
    processing = split_equal(fee.processing_fee, parts)
    gst = split_equal(fee.gst, parts)
    amounts = split_equal(fee.total, parts)
    return [
        Instalment(
            i + 1,
            enrol_date + timedelta(days=offset),
            tuition[i],
            material[i],
            exam_series[i],
            processing[i],
            gst[i],
            amounts[i],
        )
        for i, offset in enumerate(offsets)
    ]