from dataclasses import dataclass

from src.allocation.allocation import STAR_MIN_WAIVER, seat_student


@dataclass(frozen=True)
class WaitEntry:
    enrol_id: str
    student_id: str
    course_id: str
    centre_id: str
    medium: str
    timing: str
    waiver_pct: int

    @property
    def preference(self):
        return (self.course_id, self.centre_id, self.medium, self.timing)


class Waitlist:
    def __init__(self):
        self.entries = []

    def add(self, entry):
        self.entries.append(entry)

    def remove(self, enrol_id):
        self.entries = [e for e in self.entries if e.enrol_id != enrol_id]

    def position(self, enrol_id):
        entry = next(e for e in self.entries if e.enrol_id == enrol_id)
        same = [e for e in self.entries if e.preference == entry.preference]
        return same.index(entry) + 1

    def next_for(self, batch):
        preference = (batch.course_id, batch.centre_id, batch.medium, batch.timing)
        for entry in self.entries:
            if entry.preference != preference:
                continue
            if batch.is_star and entry.waiver_pct < STAR_MIN_WAIVER:
                continue
            return entry
        return None

    def promote_into(self, batch):
        if batch.seats_left <= 0:
            return None
        entry = self.next_for(batch)
        if entry is None:
            return None
        self.remove(entry.enrol_id)
        seat_student(batch, entry.enrol_id)
        return entry