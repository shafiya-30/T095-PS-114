import sys

from src.engine import Engine
from src.events.parser import parse_commands


def main(data_dir="data", out_dir="output"):
    engine = Engine(data_dir)
    engine.run(parse_commands(f"{data_dir}/commands.txt"))
    engine.write_outputs(out_dir)


if __name__ == "__main__":
    main(*sys.argv[1:])