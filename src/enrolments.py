from dataclasses import dataclass, field
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
    original_batch_id: str | None = None
    status: str = "ALLOCATED"
    merged_from: str | None = None
    merge_notice: date | None = None
    free_transfers_used: int = 0
    extra_charges: list = field(default_factory=list)