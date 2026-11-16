import csv
from pathlib import Path

import pytest

from src.engine import SCORE_COLUMNS, Engine
from src.events.parser import parse_commands

DATA = Path(__file__).resolve().parent.parent / "data"

pytestmark = pytest.mark.skipif(
    not (DATA / "commands.txt").exists(), reason="sample data not present"
)


@pytest.fixture(scope="module")
def scores(tmp_path_factory):
    out = tmp_path_factory.mktemp("out")
    engine = Engine(DATA)
    engine.run(parse_commands(DATA / "commands.txt"))
    engine.write_outputs(out)
    with open(out / "scores.csv", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        return header, list(reader)


def row(scores, test_id, student_id):
    return next(r for r in scores[1] if r["test_id"] == test_id and r["student_id"] == student_id)


def test_header_has_readme_columns_in_order(scores):
    assert tuple(scores[0]) == SCORE_COLUMNS


def test_one_row_per_response(scores):
    rows = scores[1]
    assert len([r for r in rows if r["test_id"] == "SCH-01"]) == 180
    assert len([r for r in rows if r["test_id"] == "SCH-02"]) == 20


def test_rows_ordered_by_total_desc_then_student_id(scores):
    block = [r for r in scores[1] if r["test_id"] == "SCH-01"]
    keys = [(-int(r["total"]), r["student_id"]) for r in block]
    assert keys == sorted(keys)


def test_percentile_exactly_95(scores):
    r = row(scores, "SCH-01", "STD-0009")
    assert (r["total"], r["percentile"], r["cutoff_passed"], r["waiver_pct"]) == ("158", "95.00", "true", "75")


def test_section_exactly_at_cutoff(scores):
    r = row(scores, "SCH-01", "STD-0164")
    assert (r["che"], r["cutoff_passed"], r["waiver_pct"]) == ("24", "true", "75")


def test_section_one_mark_under_cutoff(scores):
    r = row(scores, "SCH-01", "STD-0026")
    assert (r["apt"], r["percentile"], r["cutoff_passed"], r["waiver_pct"]) == ("23", "97.78", "false", "25")


def test_retest_rows_carry_their_own_waiver(scores):
    assert row(scores, "SCH-02", "STD-0096")["waiver_pct"] == "90"
    assert row(scores, "SCH-02", "STD-0073")["waiver_pct"] == "0"