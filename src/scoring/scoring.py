from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

SECTION_RANGES = {"PHY": range(0, 20), "CHE": range(20, 40), "APT": range(40, 60)}
SECTION_CUTOFF = 24
CAPPED_WAIVER = 25
ENROL_WINDOW_DAYS = 15
WAIVER_BANDS = (
    (Decimal("99"), 90),
    (Decimal("95"), 75),
    (Decimal("90"), 50),
    (Decimal("80"), 25),
)


@dataclass(frozen=True)
class Score:
    test_id: str
    student_id: str
    phy: int
    che: int
    apt: int
    total: int
    percentile: Decimal
    cutoff_passed: bool
    waiver_pct: int


def mark(answer, correct):
    if answer == "-":
        return 0
    return 4 if answer == correct else -1


def section_scores(answers, key):
    return {
        name: sum(mark(answers[i], key[i]) for i in idx)
        for name, idx in SECTION_RANGES.items()
    }


def percentile(total, totals):
    at_or_below = sum(1 for t in totals if t <= total)
    return (Decimal(100 * at_or_below) / Decimal(len(totals))).quantize(
        Decimal("0.01"), ROUND_HALF_UP
    )


def waiver_for(pct, cutoff_passed):
    band = next((w for floor, w in WAIVER_BANDS if pct >= floor), 0)
    return band if cutoff_passed else min(band, CAPPED_WAIVER)


def score_cohort(test_id, responses, key):
    raw = []
    for r in responses:
        sections = section_scores(r["answers"], key)
        raw.append((r["student_id"], sections, sum(sections.values())))
    totals = [total for _, _, total in raw]
    result = []
    for student_id, sections, total in raw:
        passed = all(v >= SECTION_CUTOFF for v in sections.values())
        pct = percentile(total, totals)
        result.append(
            Score(
                test_id,
                student_id,
                sections["PHY"],
                sections["CHE"],
                sections["APT"],
                total,
                pct,
                passed,
                waiver_for(pct, passed),
            )
        )
    return sorted(result, key=lambda s: (-s.total, s.student_id))


def better_waiver(*waivers):
    return max(waivers)


def waiver_valid(result_date, enrol_date):
    return (enrol_date - result_date).days <= ENROL_WINDOW_DAYS