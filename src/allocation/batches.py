import csv
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Batch:
    batch_id: str
    course_id: str
    centre_id: str
    medium: str
    timing: str
    batch_type: str
    start_date: date
    capacity: int
    confirmed: int
    students: list = field(default_factory=list)

    @property
    def seats_left(self):
        return self.capacity - self.confirmed

    @property
    def is_star(self):
        return self.batch_type == "STAR"


def load_batches(path):
    batches = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            batches[row["batch_id"]] = Batch(
                batch_id=row["batch_id"],
                course_id=row["course_id"],
                centre_id=row["centre_id"],
                medium=row["medium"],
                timing=row["timing"],
                batch_type=row["batch_type"],
                start_date=date.fromisoformat(row["start_date"]),
                capacity=int(row["capacity"]),
                confirmed=int(row["seats_already_confirmed"]),
            )
    return batches