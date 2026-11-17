from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.billing.late import is_suspended, late_fee

ZERO = Decimal("0.00")


@dataclass
class InstalmentState:
    instalment: object
    paid: Decimal = ZERO
    settled_on: date | None = None
    late_fee_charged: Decimal = ZERO

    def is_settled_on(self, as_of):
        return self.settled_on is not None and self.settled_on <= as_of

    def late_fee_on(self, as_of):
        if self.is_settled_on(as_of):
            return self.late_fee_charged
        return late_fee(self.instalment.due_date, as_of)

    def owed_on(self, as_of):
        return self.instalment.amount + late_fee(self.instalment.due_date, as_of) - self.paid


class Ledger:
    def __init__(self, schedule):
        self.items = [InstalmentState(i) for i in schedule]

    def pay(self, amount, pay_date):
        remaining = amount
        for item in self.items:
            if remaining <= ZERO:
                break
            if item.settled_on is not None:
                continue
            owed = item.owed_on(pay_date)
            applied = min(remaining, owed)
            item.paid += applied
            remaining -= applied
            if applied >= owed:
                item.settled_on = pay_date
                item.late_fee_charged = late_fee(item.instalment.due_date, pay_date)
        return remaining

    def settled_count(self):
        return sum(1 for item in self.items if item.settled_on is not None)

    def access_status(self, as_of):
        for item in self.items:
            if is_suspended(item.instalment.due_date, as_of, item.settled_on):
                return "SUSPENDED"
        return "ACTIVE"

    def balance_on(self, as_of):
        return sum(
            (i.instalment.amount + i.late_fee_on(as_of) - i.paid for i in self.items), ZERO
        )