from datetime import date

from src.allocation.batches import Batch
from src.allocation.waitlist import WaitEntry, Waitlist


def entry(enrol_id, waiver=0, timing="MORNING"):
    return WaitEntry(enrol_id, "STD-" + enrol_id, "NEET-1Y", "CTR-03", "ENGLISH", timing, waiver)


def batch(batch_type="REGULAR", confirmed=59):
    return Batch("B", "NEET-1Y", "CTR-03", "ENGLISH", "MORNING", batch_type, date(2026, 4, 27), 60, confirmed)


def test_positions_follow_arrival_order():
    wl = Waitlist()
    for e in ("A", "B", "C"):
        wl.add(entry(e))
    assert [wl.position(e) for e in ("A", "B", "C")] == [1, 2, 3]


def test_positions_are_per_preference():
    wl = Waitlist()
    wl.add(entry("A"))
    wl.add(entry("B", timing="EVENING"))
    assert wl.position("B") == 1


def test_removal_moves_everyone_up():
    wl = Waitlist()
    for e in ("A", "B", "C"):
        wl.add(entry(e))
    wl.remove("A")
    assert wl.position("B") == 1
    assert wl.position("C") == 2


def test_open_seat_goes_to_first_in_line():
    wl = Waitlist()
    wl.add(entry("A"))
    wl.add(entry("B"))
    b = batch()
    promoted = wl.promote_into(b)
    assert promoted.enrol_id == "A"
    assert b.confirmed == 60
    assert b.students == ["A"]
    assert [e.enrol_id for e in wl.entries] == ["B"]


def test_full_batch_promotes_nobody():
    wl = Waitlist()
    wl.add(entry("A"))
    assert wl.promote_into(batch(confirmed=60)) is None
    assert len(wl.entries) == 1


def test_star_seat_skips_low_waiver_students():
    wl = Waitlist()
    wl.add(entry("A", waiver=25))
    wl.add(entry("B", waiver=75))
    promoted = wl.promote_into(batch("STAR"))
    assert promoted.enrol_id == "B"


def test_other_preferences_are_not_promoted():
    wl = Waitlist()
    wl.add(entry("A", timing="EVENING"))
    assert wl.promote_into(batch()) is None