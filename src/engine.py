from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.allocation.allocation import choose_batch, seat_student
from src.allocation.batches import load_batches
from src.allocation.viability import check_viability
from src.allocation.waitlist import WaitEntry, Waitlist
from src.billing.fees import compute_fee, load_courses
from src.billing.ledger import Ledger
from src.billing.referral import referral_credit
from src.billing.refunds import gst_refund, material_refund, refund_percent, tuition_refund, money
from src.billing.schedule import build_schedule
from src.enrolments import Enrolment
from src.reports.writers import write_csv
from src.scoring.loader import load_answer_keys, load_responses
from src.scoring.scoring import effective_waiver, score_cohort
from src.students import load_students

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

REFUND_COLUMNS = (
    "enrol_id",
    "request_date",
    "refund_pct",
    "tuition_refund",
    "material_refund",
    "gst_refund",
    "total_refund",
)
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
        self.refund_rows = []
        self.enrolments = {}
        self.ledgers = {}
        self.referral_credits = {}
        self.waitlist = Waitlist()

    def publish_result(self, test_id, result_date):
        self.result_dates[test_id] = date.fromisoformat(result_date)

    def print_scores(self, test_id):
        table = self.all_scores[test_id]
        ordered = sorted(table.values(), key=lambda s: (-s.total, s.student_id))
        self.score_rows.extend(asdict(s) for s in ordered)

    def waiver_on(self, student_id, enrol_date):
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
            self.referral_credits[referrer] = self.referral_credits.get(referrer, Decimal("0.00")) + credit

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
                    "other_charges": Decimal("0.00"),
                    "gst": i.gst,
                    "amount": i.amount,
                    "paid": item.paid,
                    "late_fee": late,
                    "balance": i.amount + late - item.paid,
                    "access_status": access,
                }
            )
    def _batch_start(self, batch_id):
        batches = self.batches.values() if isinstance(self.batches, dict) else self.batches
        for b in batches:
            if b.batch_id == batch_id:
                return b.start_date
        return None

    def dropout(self, enrol_id, request_date, unopened):
        enrolment = self.enrolments.get(enrol_id)
        ledger = self.ledgers.get(enrol_id)
        if enrolment is None or ledger is None:
            return
        request = date.fromisoformat(request_date)
        start = self._batch_start(enrolment.batch_id)
        if start is None:
            return
        is_unopened = unopened.strip().lower() == "true"
        settled = [i for i in ledger.items if i.settled_on is not None]
        tuition_paid = sum((i.instalment.tuition for i in settled), Decimal("0.00"))
        material_paid = sum((i.instalment.material for i in settled), Decimal("0.00"))
        tuition = tuition_refund(tuition_paid, start, request)
        material = material_refund(material_paid, is_unopened, start, request)
        gst = gst_refund(tuition + material)
        self.refund_rows.append(
            {
                "enrol_id": enrol_id,
                "request_date": request,
                "refund_pct": refund_percent(start, request),
                "tuition_refund": tuition,
                "material_refund": material,
                "gst_refund": gst,
                "total_refund": money(tuition + material + gst),
            }
        )
        enrolment.status = "DROPPED"

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

    def run(self, commands):
        for command in commands:
            self.execute(command)

    def write_outputs(self, out_dir):
        write_csv(Path(out_dir) / "scores.csv", SCORE_COLUMNS, self.score_rows)
        write_csv(Path(out_dir) / "allocations.csv", ALLOCATION_COLUMNS, self.allocation_rows)
        write_csv(Path(out_dir) / "fee_statements.csv", STATEMENT_COLUMNS, self.statement_rows)
        write_csv(Path(out_dir) / "refund_orders.csv", REFUND_COLUMNS, self.refund_rows)