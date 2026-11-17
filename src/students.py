import csv
from dataclasses import dataclass


@dataclass(frozen=True)
class Student:
    student_id: str
    sibling_of: str | None
    referred_by: str | None


def load_students(path):
    students = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            students[row["student_id"]] = Student(
                row["student_id"],
                row["sibling_of"] or None,
                row["referred_by"] or None,
            )
    return students