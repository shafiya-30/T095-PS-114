from dataclasses import asdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.allocation.allocation import choose_batch, seat_student
from src.allocation.batches import load_batches
from src.allocation.viability import check_viability
from src.allocation.waitlist import WaitEntry, Waitlist
from src.billing.changes import evaluate_course_change, evaluate_transfer
from src.billing.fees import compute_fee, load_courses
from src.billing.late import can_choose_plan_4
from src.billing.ledger import Ledger
from src.billing.referral import referral_credit
from src.billing.schedule import build_schedule
from src.billing.suspensions import suspension_episodes
from src.enrolments import Enrolment
from src.refunds.refunds import compute_refund, merge_refund_eligible
from src.reports.writers import write_csv
from src.scoring.loader import load_answer_keys, load_responses
from src.scoring.scoring import effective_waiver, score_cohort
from src.students import load_students

ZERO = Decimal("0.00")
FORFEITURE_DAYS = 365
VALID_PLANS = (1, 2, 4)

ARITY = {
    "PUBLISH_RESULT": 2,
    "PRINT_SCORES": 1,
    "ENROL": 8,
    "VIABILITY_CHECK": 2,
    "PRINT_ALLOCATION": 1,
    "PAYMENT": 5,
    "PRINT_FEE_STATEMENT": 2,
    "DROPOUT": 3,
    "PRINT_REFUND_ORDERS": 2,
    "PRINT_WAITLIST": 1,
    "TRANSFER": 3,
    "UPGRADE": 4,
}

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


class InvalidCommand(Exception):
    def __init__(self, reason, detail=""):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


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
        self.centres = {b.centre_id for b in self.batches.values()}
        self.mediums = {b.medium for b in self.batches.values()}
        self.timings = {b.timing for b in self.batches.values()}
        self.result_dates = {}
        self.score_rows = []
        self.allocation_rows = []
        self.statement_rows = []
        self.refund_orders = []
        self.refund_rows = []
        self.waitlist_rows = []
        self.enrolments = {}
        self.ledgers = {}
        self.payment_ids = set()
        self.referral_credits = {}
        self.waiver_forfeitures = {}
        self.rejections = []
        self.errors = []
        self.promotions = []
        self.waitlist = Waitlist()
        self.handlers = {
            "PUBLISH_RESULT": self.publish_result,
            "PRINT_SCORES": self.print_scores,
            "ENROL": self.enrol,
            "VIABILITY_CHECK": self.viability_check,
            "PRINT_ALLOCATION": self.print_allocation,
            "PAYMENT": self.payment,
            "PRINT_FEE_STATEMENT": self.print_fee_statement,
            "DROPOUT": self.dropout,
            "PRINT_REFUND_ORDERS": self.print_refund_orders,
            "PRINT_WAITLIST": self.print_waitlist,
            "TRANSFER": self.transfer,
            "UPGRADE": self.upgrade,
        }

    def parse_date(self, text):
        try:
            return date.fromisoformat(text)
        except (TypeError, ValueError):
            raise InvalidCommand("INVALID_DATE", str(text))

    def parse_amount(self, text):
        try:
            value = Decimal(text)
        except (InvalidOperation, TypeError):
            raise InvalidCommand("INVALID_AMOUNT", str(text))
        if not value.is_finite() or value <= 0:
            raise InvalidCommand("INVALID_AMOUNT", str(text))
        return value

    def parse_plan(self, text):
        try:
            plan = int(text)
        except (TypeError, ValueError):
            raise InvalidCommand("INVALID_PLAN", str(text))
        if plan not in VALID_PLANS:
            raise InvalidCommand("INVALID_PLAN", str(text))
        return plan

    def known(self, table, key, reason):
        if key not in table:
            raise InvalidCommand(reason, str(key))
        return table[key]

    def live_enrolment(self, enrol_id):
        enrolment = self.known(self.enrolments, enrol_id, "UNKNOWN_ENROLMENT")
        if enrolment.status == "DROPPED":
            raise InvalidCommand("ALREADY_DROPPED", enrol_id)
        if enrol_id not in self.ledgers:
            raise InvalidCommand("NOT_SEATED", enrol_id)
        return enrolment

    def publish_result(self, test_id, result_date):
        self.known(self.all_scores, test_id, "UNKNOWN_TEST")
        self.result_dates[test_id] = self.parse_date(result_date)

    def print_scores(self, test_id):
        table = self.known(self.all_scores, test_id, "UNKNOWN_TEST")
        if test_id not in self.result_dates:
            raise InvalidCommand("RESULT_NOT_PUBLISHED", test_id)
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

    def suspension_count(self, student_id, as_of):
        pairs = [
            (item.instalment.due_date, item.settled_on)
            for e in self.enrolments.values()
            if e.student_id == student_id and e.enrol_id in self.ledgers
            for item in self.ledgers[e.enrol_id].items
        ]
        return suspension_episodes(pairs, as_of)

    def open_ledger(self, enrolment, start):
        fee = compute_fee(
            self.courses[enrolment.course_id],
            enrolment.waiver_pct,
            enrolment.has_sibling,
            enrolment.plan,
        )
        ledger = Ledger(build_schedule(fee, enrolment.plan, start))
        ledger.pay(ledger.items[0].instalment.amount, start)
        self.ledgers[enrolment.enrol_id] = ledger

    def enrol(self, enrol_id, student_id, enrol_date, course_id, centre_id, medium, timing, plan):
        when = self.parse_date(enrol_date)
        if enrol_id in self.enrolments:
            raise InvalidCommand("DUPLICATE_ENROLMENT", enrol_id)
        student = self.known(self.students, student_id, "UNKNOWN_STUDENT")
        self.known(self.courses, course_id, "UNKNOWN_COURSE")
        if centre_id not in self.centres:
            raise InvalidCommand("UNKNOWN_CENTRE", str(centre_id))
        if medium not in self.mediums:
            raise InvalidCommand("INVALID_MEDIUM", str(medium))
        if timing not in self.timings:
            raise InvalidCommand("INVALID_TIMING", str(timing))
        plan_number = self.parse_plan(plan)
        if plan_number == 4 and not can_choose_plan_4(self.suspension_count(student_id, when)):
            raise InvalidCommand("PLAN_4_NOT_AVAILABLE", student_id)
        waiver = self.waiver_on(student_id, when)
        enrolment = Enrolment(
            enrol_id,
            student_id,
            when,
            course_id,
            centre_id,
            medium,
            timing,
            plan_number,
            waiver,
            student.sibling_of is not None,
        )
        batch = choose_batch(self.batches, course_id, centre_id, medium, timing, waiver)
        if batch is None:
            enrolment.status = "WAITLISTED"
            self.waitlist.add(WaitEntry(enrol_id, student_id, course_id, centre_id, medium, timing, waiver))
        else:
            seat_student(batch, enrol_id)
            enrolment.batch_id = batch.batch_id
            enrolment.original_batch_id = batch.batch_id
            self.open_ledger(enrolment, when)
        self.enrolments[enrol_id] = enrolment

    def fill_seat(self, batch, when):
        entry = self.waitlist.promote_into(batch)
        if entry is None:
            return
        enrolment = self.enrolments[entry.enrol_id]
        enrolment.status = "ALLOCATED"
        enrolment.batch_id = batch.batch_id
        enrolment.original_batch_id = batch.batch_id
        self.open_ledger(enrolment, when)
        self.promotions.append({"enrol_id": entry.enrol_id, "batch_id": batch.batch_id, "date": when})

    def viability_check(self, batch_id, check_date):
        self.known(self.batches, batch_id, "UNKNOWN_BATCH")
        notice = self.parse_date(check_date)
        result = check_viability(self.batches, batch_id)
        if result is None:
            return
        target, moved = result
        for enrol_id in moved:
            enrolment = self.enrolments[enrol_id]
            enrolment.status = "MERGED"
            enrolment.merged_from = batch_id
            enrolment.merge_notice = notice
            enrolment.batch_id = target.batch_id

    def print_allocation(self, batch_id):
        self.known(self.batches, batch_id, "UNKNOWN_BATCH")
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
        paid_on = self.parse_date(payment_date)
        enrolment = self.live_enrolment(enrol_id)
        value = self.parse_amount(amount)
        if payment_id in self.payment_ids:
            raise InvalidCommand("DUPLICATE_PAYMENT", payment_id)
        self.payment_ids.add(payment_id)
        ledger = self.ledgers[enrol_id]
        before = ledger.settled_count()
        ledger.pay(value, paid_on)
        credit = referral_credit(before, ledger.settled_count())
        referrer = self.students[enrolment.student_id].referred_by
        if credit and referrer:
            self.referral_credits[referrer] = self.referral_credits.get(referrer, ZERO) + credit

    def print_fee_statement(self, enrol_id, as_of_date):
        as_of = self.parse_date(as_of_date)
        self.known(self.enrolments, enrol_id, "UNKNOWN_ENROLMENT")
        ledger = self.ledgers.get(enrol_id)
        if ledger is None:
            return
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
        request = self.parse_date(request_date)
        enrolment = self.known(self.enrolments, enrol_id, "UNKNOWN_ENROLMENT")
        if enrolment.status == "DROPPED":
            raise InvalidCommand("ALREADY_DROPPED", enrol_id)
        if enrolment.status == "WAITLISTED":
            self.waitlist.remove(enrol_id)
            enrolment.status = "DROPPED"
            return
        ledger = self.ledgers[enrol_id]
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
        self.fill_seat(current, request)

    def print_refund_orders(self, from_date, to_date):
        start = self.parse_date(from_date)
        end = self.parse_date(to_date)
        if start > end:
            raise InvalidCommand("INVALID_DATE_RANGE", f"{from_date} to {to_date}")
        chosen = sorted(
            (o for o in self.refund_orders if start <= o.request_date <= end),
            key=lambda o: o.request_date,
        )
        self.refund_rows.extend(asdict(o) for o in chosen)

    def print_waitlist(self, as_of_date):
        as_of = self.parse_date(as_of_date)
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

    def move_seat(self, enrolment, target, when):
        current = self.batches[enrolment.batch_id]
        current.confirmed -= 1
        current.students.remove(enrolment.enrol_id)
        seat_student(target, enrolment.enrol_id)
        enrolment.batch_id = target.batch_id
        enrolment.centre_id = target.centre_id
        enrolment.medium = target.medium
        enrolment.timing = target.timing
        self.fill_seat(current, when)

    def reject(self, command_name, enrol_id, reason):
        self.rejections.append({"command": command_name, "enrol_id": enrol_id, "reason": reason})

    def transfer(self, enrol_id, transfer_date, to_batch_id):
        when = self.parse_date(transfer_date)
        enrolment = self.live_enrolment(enrol_id)
        source = self.batches[enrolment.batch_id]
        target = self.known(self.batches, to_batch_id, "UNKNOWN_BATCH")
        change = evaluate_transfer(source, target, enrolment.free_transfers_used)
        if not change.allowed:
            self.reject("TRANSFER", enrol_id, change.reason)
            return
        self.move_seat(enrolment, target, when)
        enrolment.status = "TRANSFERRED"
        if change.reason == "FREE_TRANSFER":
            enrolment.free_transfers_used += 1
        enrolment.extra_charges.append((when, change.reason, change.amount))

    def upgrade(self, enrol_id, change_date, new_course_id, new_batch_id):
        when = self.parse_date(change_date)
        enrolment = self.live_enrolment(enrol_id)
        new_course = self.known(self.courses, new_course_id, "UNKNOWN_COURSE")
        target = self.known(self.batches, new_batch_id, "UNKNOWN_BATCH")
        if target.course_id != new_course_id:
            raise InvalidCommand("BATCH_COURSE_MISMATCH", f"{new_batch_id} is not {new_course_id}")
        current = self.batches[enrolment.batch_id]
        change = evaluate_course_change(
            self.courses[enrolment.course_id],
            new_course,
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
        self.move_seat(enrolment, target, when)
        enrolment.course_id = new_course_id
        enrolment.extra_charges.append((when, change.reason, change.amount))

    def fail(self, command, reason, detail):
        self.errors.append(
            {"line": command.line_no, "command": command.name, "reason": reason, "detail": detail}
        )

    def execute(self, command):
        handler = self.handlers.get(command.name)
        if handler is None:
            self.fail(command, "UNKNOWN_COMMAND", command.name)
            return
        if len(command.args) != ARITY[command.name]:
            self.fail(
                command,
                "WRONG_ARGUMENT_COUNT",
                f"expected {ARITY[command.name]}, got {len(command.args)}",
            )
            return
        try:
            handler(*command.args)
        except InvalidCommand as problem:
            self.fail(command, problem.reason, problem.detail)
        except (KeyError, ValueError, TypeError, AttributeError) as problem:
            self.fail(command, "UNEXPECTED_ERROR", repr(problem))

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