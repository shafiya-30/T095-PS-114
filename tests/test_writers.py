import csv
from datetime import date
from decimal import Decimal

from src.reports.writers import cell, write_csv


def read(path):
    with open(path, newline="") as f:
        return list(csv.reader(f))


def test_header_then_rows_in_column_order(tmp_path):
    path = tmp_path / "out.csv"
    write_csv(path, ("b", "a"), [{"a": 1, "b": 2}, {"a": 3, "b": 4}])
    assert read(path) == [["b", "a"], ["2", "1"], ["4", "3"]]


def test_values_are_written_in_readme_format():
    assert cell(True) == "true"
    assert cell(False) == "false"
    assert cell(None) == ""
    assert cell(Decimal("95.00")) == "95.00"
    assert cell(date(2026, 4, 9)) == "2026-04-09"
    assert cell(75) == "75"


def test_missing_folder_is_created(tmp_path):
    path = tmp_path / "nested" / "out.csv"
    write_csv(path, ("a",), [{"a": 1}])
    assert path.exists()


def test_no_rows_still_writes_header(tmp_path):
    path = tmp_path / "out.csv"
    write_csv(path, ("a", "b"), [])
    assert read(path) == [["a", "b"]]