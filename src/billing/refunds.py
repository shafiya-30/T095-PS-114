from datetime import date
from decimal import Decimal, ROUND_HALF_UP

GST_RATE = Decimal("0.18")
MATERIAL_WINDOW_DAYS = 15


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# BR-07: refund ladder, counted from the batch start date
def refund_percent(batch_start: date, request_date: date) -> Decimal:
    days = (request_date - batch_start).days
    if days < 0:
        return Decimal("0.90")
    if days <= 15:
        return Decimal("0.75")
    if days <= 30:
        return Decimal("0.50")
    if days <= 60:
        return Decimal("0.25")
    return Decimal("0.00")


# BR-08: refund base is net tuition actually paid (after waiver)
def tuition_refund(net_tuition_paid, batch_start, request_date):
    return money(Decimal(net_tuition_paid) * refund_percent(batch_start, request_date))


# BR-07: material refunded only if unopened and within 15 days of start
def material_refund(material_paid, unopened, batch_start, request_date):
    days = (request_date - batch_start).days
    if unopened and days <= MATERIAL_WINDOW_DAYS:
        return money(material_paid)
    return Decimal("0.00")


# BR-07: GST is refunded in proportion to the refunded amount
def gst_refund(refundable_amount):
    return money(Decimal(refundable_amount) * GST_RATE)


def total_refund(net_tuition_paid, material_paid, unopened, batch_start, request_date):
    base = tuition_refund(net_tuition_paid, batch_start, request_date)
    base += material_refund(material_paid, unopened, batch_start, request_date)
    return money(base + gst_refund(base))