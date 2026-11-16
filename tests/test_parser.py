from pathlib import Path

import pytest

from src.events.parser import Command, parse_commands, parse_lines

DATA = Path(__file__).resolve().parent.parent / "data"

needs_data = pytest.mark.skipif(
    not (DATA / "commands.txt").exists(), reason="sample data not present"
)


def test_comments_and_blank_lines_are_skipped():
    lines = ["# header", "", "PUBLISH_RESULT|SCH-01|2026-03-25", "   "]
    assert list(parse_lines(lines)) == [
        Command(3, "PUBLISH_RESULT", ("SCH-01", "2026-03-25"))
    ]


def test_line_numbers_are_physical_lines_including_comments():
    lines = ["# one", "# two", "PRINT_SCORES|SCH-01"]
    assert next(parse_lines(lines)).line_no == 3


def test_dash_means_not_applicable():
    command = next(parse_lines(["TRANSFER|ENR-0001|2026-04-29|-"]))
    assert command.args == ("ENR-0001", "2026-04-29", None)


def test_command_without_arguments():
    command = next(parse_lines(["SOMETHING"]))
    assert command.name == "SOMETHING"
    assert command.args == ()


@needs_data
def test_sample_file_has_150_enrolments_and_150_statements():
    commands = parse_commands(DATA / "commands.txt")
    names = [c.name for c in commands]
    assert names[0] == "PUBLISH_RESULT"
    assert names.count("ENROL") == 150
    assert names.count("PRINT_FEE_STATEMENT") == 150


@needs_data
def test_planted_enrolment_lines_match_readme():
    by_line = {c.line_no: c for c in parse_commands(DATA / "commands.txt")}
    assert by_line[141].name == "ENROL"
    assert by_line[141].args[1] == "STD-0095"
    assert by_line[145].args[1] == "STD-0015"