from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.allocation.allocation import choose_batch, seat_student
from src.allocation.batches import load_batches
from src.allocation.viability import check_viability
from src.allocation.waitlist import WaitEntry, Waitlist
from src.billing.changes import evaluate_course_change, evaluate_transfer
from src.billing.fees import compute_fee, load_courses
from src.billing.ledger import Ledger
from src.billing.referral import referral_credit
from src.billing.schedule import build_schedule
from src.enrolments import Enrolment
from src.refunds.refunds import compute_refund, merge_refund_eligible
from src.reports.writers import write_csv
from src.scoring.loader import load_answer_keys, load_responses
from src.scoring.scoring import effective_waiver, score_cohort
from src.students import load_students

ZERO = Decimal("0.00")
FORFEITURE_DAYS = 365

SCORE_COLUMNS = (
    "test_id",
    "student_id",
    "phy",
    "che",
    "apt",
    "total",
    "percentile",
    "cutoff_passed",
    "waiver_pct",
)

ALLOCATION_COLUMNS = ("batch_id", "enrol_id", "student_id", "waiver_pct", "status")

STATEMENT_COLUMNS = (
    "enrol_id",
    "as_of_date",
    "instalment_no",
    "due_date",
    "tuition",
    "material",
    "exam_series",
    "processing_fee",
    "other_charges",
    "gst",
    "amount",
    "paid",
    "late_fee",
    "balance",
    "access_status",
)

REFUND_COLUMNS = (
    "enrol_id",
    "request_date",
    "days_from_start",
    "refund_pct",
    "tuition_refund",
    "material_refund",
    "gst_refund",
    "total_refund",
    "waiver_forfeited",
)

WAITLIST_COLUMNS = (
    "as_of_date",
    "enrol_id",
    "student_id",
    "course_id",
    "centre_id",
    "medium",
    "timing",
    "position",
)


class Engine:
    def __init__(self, data_dir):
        data = Path(data_dir)
        self.keys = load_answer_keys(data / "answer_key.csv")
        self.responses = load_responses(data / "test_responses.csv")
        self.students = load_students(data / "students.csv")
        self.batches = load_batches(data / "batches.csv")
        self.courses = load_courses(data / "courses.csv")
        self.all_scores = {
            test_id: {s.student_id: s for s in score_cohort(test_id, rows, self.keys[test_id])}
            for test_id, rows in self.responses.items()
        }
        self.result_dates = {}
        self.score_rows = []
        self.allocation_rows = []
        self.statement_rows = []
        self.refund_orders = []
        self.refund_rows = []
        self.waitlist_rows = []
        self.enrolments = {}
        self.ledgers = {}
        self.referral_credits = {}
        self.waiver_forfeitures = {}
        self.rejections = []
        self.waitlist = Waitlist()

    def publish_result(self, test_id, result_date):
        self.result_dates[test_id] = date.fromisoformat(result_date)

    def print_scores(self, test_id):
        table = self.all_scores[test_id]
        ordered = sorted(table.values(), key=lambda s: (-s.total, s.student_id))
        self.score_rows.extend(asdict(s) for s in ordered)

    def waiver_on(self, student_id, enrol_date):
        forfeited_on = self.waiver_forfeitures.get(student_id)
        if forfeited_on and 0 <= (enrol_date - forfeited_on).days <= FORFEITURE_DAYS:
            return 0
        sat = [t for t, table in self.all_scores.items() if student_id in table]
        published = [self.result_dates[t] for t in sat if t in self.result_dates]
        if not published:
            return 0
        window_start = min(published)
        attempts = [(self.all_scores[t][student_id].waiver_pct, window_start) for t in sat]
        return effective_waiver(attempts, enrol_date)

    def open_ledger(self, enrolment):
        fee = compute_fee(
            self.courses[enrolment.course_id],
            enrolment.waiver_pct,
            enrolment.has_sibling,
            enrolment.plan,
        )
        ledger = Ledger(build_schedule(fee, enrolment.plan, enrolment.enrol_date))
        ledger.pay(ledger.items[0].instalment.amount, enrolment.enrol_date)
        self.ledgers[enrolment.enrol_id] = ledger

    def enrol(self, enrol_id, student_id, enrol_date, course_id, centre_id, medium, timing, plan):
        enrol_date = date.fromisoformat(enrol_date)
        waiver = self.waiver_on(student_id, enrol_date)
        enrolment = Enrolment(
            enrol_id,
            student_id,
            enrol_date,
            course_id,
            centre_id,
            medium,
            timing,
            int(plan),
            waiver,
            self.students[student_id].sibling_of is not None,
        )
        batch = choose_batch(self.batches, course_id, centre_id, medium, timing, waiver)
        if batch is None:
            enrolment.status = "WAITLISTED"
            self.waitlist.add(WaitEntry(enrol_id, student_id, course_id, centre_id, medium, timing, waiver))
        else:
            seat_student(batch, enrol_id)
            enrolment.batch_id = batch.batch_id
            enrolment.original_batch_id = batch.batch_id
            self.open_ledger(enrolment)
        self.enrolments[enrol_id] = enrolment

    def viability_check(self, batch_id, check_date):
        result = check_viability(self.batches, batch_id)
        if result is None:
            return
        target, moved = result
        notice = date.fromisoformat(check_date)
        for enrol_id in moved:
            enrolment = self.enrolments[enrol_id]
            enrolment.status = "MERGED"
            enrolment.merged_from = batch_id
            enrolment.merge_notice = notice
            enrolment.batch_id = target.batch_id

    def print_allocation(self, batch_id):
        for e in self.enrolments.values():
            in_batch = e.batch_id == batch_id and e.merged_from is None
            if in_batch or e.merged_from == batch_id:
                self.allocation_rows.append(
                    {
                        "batch_id": batch_id,
                        "enrol_id": e.enrol_id,
                        "student_id": e.student_id,
                        "waiver_pct": e.waiver_pct,
                        "status": e.status,
                    }
                )

    def payment(self, payment_id, enrol_id, payment_date, amount, mode):
        ledger = self.ledgers.get(enrol_id)
        if ledger is None:
            return
        before = ledger.settled_count()
        ledger.pay(Decimal(amount), date.fromisoformat(payment_date))
        credit = referral_credit(before, ledger.settled_count())
        referrer = self.students[self.enrolments[enrol_id].student_id].referred_by
        if credit and referrer:
            self.referral_credits[referrer] = self.referral_credits.get(referrer, ZERO) + credit

    def print_fee_statement(self, enrol_id, as_of_date):
        ledger = self.ledgers.get(enrol_id)
        if ledger is None:
            return
        as_of = date.fromisoformat(as_of_date)
        access = ledger.access_status(as_of)
        for item in ledger.items:
            i = item.instalment
            late = item.late_fee_on(as_of)
            self.statement_rows.append(
                {
                    "enrol_id": enrol_id,
                    "as_of_date": as_of,
                    "instalment_no": i.no,
                    "due_date": i.due_date,
                    "tuition": i.tuition,
                    "material": i.material,
                    "exam_series": i.exam_series,
                    "processing_fee": i.processing_fee,
                    "other_charges": ZERO,
                    "gst": i.gst,
                    "amount": i.amount,
                    "paid": item.paid,
                    "late_fee": late,
                    "balance": i.amount + late - item.paid,
                    "access_status": access,
                }
            )

    def dropout(self, enrol_id, request_date, unopened):
        enrolment = self.enrolments.get(enrol_id)
        ledger = self.ledgers.get(enrol_id)
        if enrolment is None or ledger is None or enrolment.status == "DROPPED":
            return
        request = date.fromisoformat(request_date)
        origin = self.batches[enrolment.original_batch_id]
        settled = [i for i in ledger.items if i.settled_on is not None]
        merged_full = enrolment.merge_notice is not None and merge_refund_eligible(
            enrolment.merge_notice, request
        )
        order = compute_refund(
            enrol_id,
            request,
            origin.start_date,
            sum((i.instalment.tuition for i in settled), ZERO),
            sum((i.instalment.material for i in settled), ZERO),
            self.courses[enrolment.course_id].gst_pct,
            (unopened or "").strip().lower() == "true",
            origin.is_star,
            merged_full,
        )
        self.refund_orders.append(order)
        if order.waiver_forfeited:
            self.waiver_forfeitures[enrolment.student_id] = request
        current = self.batches[enrolment.batch_id]
        current.confirmed -= 1
        current.students.remove(enrol_id)
        enrolment.status = "DROPPED"

    def print_refund_orders(self, from_date, to_date):
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
        chosen = sorted(
            (o for o in self.refund_orders if start <= o.request_date <= end),
            key=lambda o: o.request_date,
        )
        self.refund_rows.extend(asdict(o) for o in chosen)

    def print_waitlist(self, as_of_date):
        as_of = date.fromisoformat(as_of_date)
        for entry in self.waitlist.entries:
            self.waitlist_rows.append(
                {
                    "as_of_date": as_of,
                    "enrol_id": entry.enrol_id,
                    "student_id": entry.student_id,
                    "course_id": entry.course_id,
                    "centre_id": entry.centre_id,
                    "medium": entry.medium,
                    "timing": entry.timing,
                    "position": self.waitlist.position(entry.enrol_id),
                }
            )

    def move_seat(self, enrolment, target):
        current = self.batches[enrolment.batch_id]
        current.confirmed -= 1
        current.students.remove(enrolment.enrol_id)
        seat_student(target, enrolment.enrol_id)
        enrolment.batch_id = target.batch_id
        enrolment.centre_id = target.centre_id
        enrolment.medium = target.medium
        enrolment.timing = target.timing

    def active(self, enrol_id):
        enrolment = self.enrolments.get(enrol_id)
        if enrolment is None or enrol_id not in self.ledgers or enrolment.status == "DROPPED":
            return None
        return enrolment

    def reject(self, command_name, enrol_id, reason):
        self.rejections.append({"command": command_name, "enrol_id": enrol_id, "reason": reason})

    def transfer(self, enrol_id, transfer_date, to_batch_id):
        enrolment = self.active(enrol_id)
        if enrolment is None:
            return
        source = self.batches[enrolment.batch_id]
        target = self.batches[to_batch_id]
        change = evaluate_transfer(source, target, enrolment.free_transfers_used)
        if not change.allowed:
            self.reject("TRANSFER", enrol_id, change.reason)
            return
        self.move_seat(enrolment, target)
        enrolment.status = "TRANSFERRED"
        if change.reason == "FREE_TRANSFER":
            enrolment.free_transfers_used += 1
        enrolment.extra_charges.append((date.fromisoformat(transfer_date), change.reason, change.amount))

    def upgrade(self, enrol_id, change_date, new_course_id, new_batch_id):
        enrolment = self.active(enrol_id)
        if enrolment is None:
            return
        current = self.batches[enrolment.batch_id]
        target = self.batches[new_batch_id]
        when = date.fromisoformat(change_date)
        change = evaluate_course_change(
            self.courses[enrolment.course_id],
            self.courses[new_course_id],
            current,
            target,
            when,
            enrolment.waiver_pct,
            enrolment.has_sibling,
            enrolment.plan,
        )
        if not change.allowed:
            self.reject("UPGRADE", enrol_id, change.reason)
            return
        self.move_seat(enrolment, target)
        enrolment.course_id = new_course_id
        enrolment.extra_charges.append((when, change.reason, change.amount))

    def execute(self, command):
        if command.name == "PUBLISH_RESULT":
            self.publish_result(*command.args)
        elif command.name == "PRINT_SCORES":
            self.print_scores(*command.args)
        elif command.name == "ENROL":
            self.enrol(*command.args)
        elif command.name == "VIABILITY_CHECK":
            self.viability_check(*command.args)
        elif command.name == "PRINT_ALLOCATION":
            self.print_allocation(*command.args)
        elif command.name == "PAYMENT":
            self.payment(*command.args)
        elif command.name == "PRINT_FEE_STATEMENT":
            self.print_fee_statement(*command.args)
        elif command.name == "DROPOUT":
            self.dropout(*command.args)
        elif command.name == "PRINT_REFUND_ORDERS":
            self.print_refund_orders(*command.args)
        elif command.name == "PRINT_WAITLIST":
            self.print_waitlist(*command.args)
        elif command.name == "TRANSFER":
            self.transfer(*command.args)
        elif command.name == "UPGRADE":
            self.upgrade(*command.args)

    def run(self, commands):
        for command in commands:
            self.execute(command)

    def write_outputs(self, out_dir):
        out = Path(out_dir)
        write_csv(out / "scores.csv", SCORE_COLUMNS, self.score_rows)
        write_csv(out / "allocations.csv", ALLOCATION_COLUMNS, self.allocation_rows)
        write_csv(out / "fee_statements.csv", STATEMENT_COLUMNS, self.statement_rows)
        write_csv(out / "refund_orders.csv", REFUND_COLUMNS, self.refund_rows)
        write_csv(out / "waitlist.csv", WAITLIST_COLUMNS, self.waitlist_rows)