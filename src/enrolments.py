from dataclasses import dataclass
from datetime import date


@dataclass
class Enrolment:
    enrol_id: str
    student_id: str
    enrol_date: date
    course_id: str
    centre_id: str
    medium: str
    timing: str
    plan: int
    waiver_pct: int
    has_sibling: bool
    batch_id: str | None = None
    status: str = "ALLOCATED"