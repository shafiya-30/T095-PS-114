from dataclasses import asdict
from datetime import date
from pathlib import Path

from src.allocation.allocation import choose_batch, seat_student
from src.allocation.batches import load_batches
from src.allocation.waitlist import WaitEntry, Waitlist
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


class Engine:
    def __init__(self, data_dir):
        data = Path(data_dir)
        self.keys = load_answer_keys(data / "answer_key.csv")
        self.responses = load_responses(data / "test_responses.csv")
        self.students = load_students(data / "students.csv")
        self.batches = load_batches(data / "batches.csv")
        self.all_scores = {
            test_id: {s.student_id: s for s in score_cohort(test_id, rows, self.keys[test_id])}
            for test_id, rows in self.responses.items()
        }
        self.result_dates = {}
        self.score_rows = []
        self.enrolments = {}
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
        self.enrolments[enrol_id] = enrolment

    def execute(self, command):
        if command.name == "PUBLISH_RESULT":
            self.publish_result(*command.args)
        elif command.name == "PRINT_SCORES":
            self.print_scores(*command.args)
        elif command.name == "ENROL":
            self.enrol(*command.args)

    def run(self, commands):
        for command in commands:
            self.execute(command)

    def write_outputs(self, out_dir):
        write_csv(Path(out_dir) / "scores.csv", SCORE_COLUMNS, self.score_rows)