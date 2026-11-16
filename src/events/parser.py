from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    line_no: int
    name: str
    args: tuple


def parse_lines(lines):
    for line_no, raw in enumerate(lines, start=1):
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        name, *args = text.split("|")
        yield Command(line_no, name, tuple(None if a == "-" else a for a in args))


def parse_commands(path):
    with open(path, encoding="utf-8") as f:
        return list(parse_lines(f))