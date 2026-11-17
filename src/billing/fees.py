
import csv
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
MAX_DISCOUNT_PCT = 90
SIBLING_PCT = 10
PLAN_ONE_PCT = 5
PROCESSING_FEE_PLAN_4 = Decimal("2000.00")
SUPPORTED_PLANS = (1, 2, 4)


@dataclass(frozen=True)
class Course:
    course_id: str
    tuition_fee: Decimal
    material_fee: Decimal
    exam_series_fee: Decimal
    gst_pct: Decimal


@dataclass(frozen=True)
class Fee:
    discount_pct: int
    tuition: Decimal
    material: Decimal
    exam_series: Decimal
    processing_fee: Decimal
    gst: Decimal
    total: Decimal


def money(value):
    return Decimal(value).quantize(CENT, ROUND_HALF_UP)


def load_courses(path):
    courses = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            courses[row["course_id"]] = Course(
                row["course_id"],
                Decimal(row["tuition_fee"]),
                Decimal(row["material_fee"]),
                Decimal(row["exam_series_fee"]),
                Decimal(row["gst_pct"]),
            )
    return courses


def total_discount_pct(waiver_pct, has_sibling):
    return min(
        waiver_pct + (SIBLING_PCT if has_sibling else 0),
        MAX_DISCOUNT_PCT
    )


def compute_fee(course, waiver_pct, has_sibling, plan):
    if plan not in SUPPORTED_PLANS:
        raise ValueError(f"Invalid payment plan: {plan}")

    discount = total_discount_pct(waiver_pct, has_sibling)

    tuition = course.tuition_fee * (100 - discount) / 100

    if plan == 1:
        tuition = tuition * (100 - PLAN_ONE_PCT) / 100

    tuition = money(tuition)

    processing = (
        PROCESSING_FEE_PLAN_4
        if plan == 4
        else Decimal("0.00")
    )

    subtotal = (
        tuition
        + course.material_fee
        + course.exam_series_fee
        + processing
    )

    gst = money(subtotal * course.gst_pct / 100)

    return Fee(
        discount,
        tuition,
        course.material_fee,
        course.exam_series_fee,
        processing,
        gst,
        subtotal + gst,
    )
