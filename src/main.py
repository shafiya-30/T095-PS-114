import sys

from src.engine import Engine
from src.events.parser import parse_commands

WIDTH = 56
LINE = "=" * WIDTH


def banner(text):
    print(LINE)
    print(text.center(WIDTH))
    print(LINE)


def section(title):
    print()
    print(title)
    print("-" * WIDTH)


def summary(engine, commands, out_dir):
    banner("COACHING INSTITUTE ENGINE - RUN SUMMARY")
    print(f"Commands processed : {len(commands)}")
    print(f"Enrolments         : {len(engine.enrolments)}")
    counts = {}
    for enrolment in engine.enrolments.values():
        counts[enrolment.status] = counts.get(enrolment.status, 0) + 1
    for status in sorted(counts):
        print(f"  {status:<12} {counts[status]:>4}")

    section("OUTPUT FILES")
    files = (
        ("scores.csv", engine.score_rows),
        ("allocations.csv", engine.allocation_rows),
        ("fee_statements.csv", engine.statement_rows),
        ("refund_orders.csv", engine.refund_rows),
        ("waitlist.csv", engine.waitlist_rows),
    )
    for name, rows in files:
        print(f"  {name:<22}{len(rows):>5} rows")

    merges = sorted({(e.merged_from, e.batch_id) for e in engine.enrolments.values() if e.merged_from})
    if merges:
        section("BATCH MERGES")
        for source, target in merges:
            print(f"  {source} merged into {target}")

    if engine.errors:
        section("INVALID COMMANDS (skipped)")
        for e in engine.errors:
            print(f"  line {e['line']:<4}{e['command']:<20}{e['reason']}  {e['detail']}")

    if engine.promotions:
        section("WAITLIST PROMOTIONS")
        for p in engine.promotions:
            print(f"  {p['enrol_id']} got a seat in {p['batch_id']} on {p['date']}")

    if engine.rejections:
        section("REJECTED REQUESTS")
        for r in engine.rejections:
            print(f"  {r['command']:<9}{r['enrol_id']}  {r['reason']}")

    if engine.refund_rows:
        section("REFUND ORDERS")
        print(f"  {'ENROL':<10}{'DATE':<12}{'DAY':>5}{'PCT':>6}{'TOTAL':>14}  WAIVER LOST")
        for r in engine.refund_rows:
            lost = "yes" if r["waiver_forfeited"] else "no"
            print(
                f"  {r['enrol_id']:<10}{str(r['request_date']):<12}"
                f"{r['days_from_start']:>5}{r['refund_pct']:>6}{str(r['total_refund']):>14}  {lost}"
            )

    if engine.waitlist_rows:
        section("WAITLIST")
        for r in engine.waitlist_rows:
            print(f"  #{r['position']} {r['enrol_id']} {r['student_id']} {r['course_id']} {r['centre_id']}")

    print()
    print(f"Files written to: {out_dir}")
    print(LINE)


def main(data_dir="data", out_dir="output"):
    engine = Engine(data_dir)
    commands = parse_commands(f"{data_dir}/commands.txt")
    engine.run(commands)
    engine.write_outputs(out_dir)
    summary(engine, commands, out_dir)


if __name__ == "__main__":
    main(*sys.argv[1:])