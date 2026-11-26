# T095-PS-114: Coaching Institute Batch Allocation, Scholarship Test and Refund Policy Engine

Team T095: Syeda Shafiya (1AT24CG091) and Tejaswini G (1AT24CG092), Section CSD. Language: Python 3.10+.

A command-file driven engine for a competitive-exam coaching institute. It scores scholarship tests with negative marking and section cut-offs and awards fee waivers. It allocates students to batches (STAR rule, capacity, waitlist, viability merge), bills fees with waiver, sibling discount, instalments, late fees and test-access suspension, and handles transfers, upgrades, dropouts, refunds and referral credits. There is no UI: it reads CSV master files plus a command file and writes five CSV files.

## Requirements

- Python 3.10 or newer
- pytest (`pip install pytest`)

## How to run

From the repository root:

```
python -m src.main
```

This reads the input files from `data/`, processes `commands.txt` in file order, prints a run summary, and writes the output files to `output/`. To use other folders:

```
python -m src.main <data_folder> <output_folder>
```

The run summary shows the number of commands and enrolments, the row count of each output file, batch merges, rejected requests, invalid commands (skipped with a reason and line number), waitlist promotions, the refund orders and the waitlist.

## How to run the tests

```
python -m pytest -q
```

There are 245 tests. Every business rule has at least one test, and the sample pack's planted scenarios are tested against the real data files.

## Input files (data folder)

| File | Content |
|---|---|
| `courses.csv` | Courses with tuition, material, exam series fee and GST |
| `centres.csv` | Centres |
| `batches.csv` | Batches with course, centre, medium, timing, STAR or REGULAR, start date, capacity and seats already confirmed |
| `answer_key.csv` | Answer key for the scholarship test SCH-01 and the re-test SCH-02 |
| `students.csv` | Candidates with sibling and referral links |
| `test_responses.csv` | Answer strings for each test |
| `commands.txt` | One command per line, in the form `NAME|arg1|arg2|...`, processed in order |

## Commands handled

`PUBLISH_RESULT`, `PRINT_SCORES`, `ENROL`, `VIABILITY_CHECK`, `PRINT_ALLOCATION`, `PAYMENT`, `PRINT_FEE_STATEMENT`, `DROPOUT`, `TRANSFER`, `UPGRADE`, `PRINT_REFUND_ORDERS`, `PRINT_WAITLIST`.

A command with an unknown student, course, centre, batch, test or enrolment, a bad date, amount or plan, or the wrong number of arguments is skipped with a clear reason, and the run continues.

## Output files

| File | Content |
|---|---|
| `scores.csv` | Section scores, total, percentile, cut-off result and waiver for each response |
| `allocations.csv` | Batch allocation lists after each `PRINT_ALLOCATION` |
| `fee_statements.csv` | One row per instalment with late fee, balance and access status |
| `refund_orders.csv` | One row per refund with days from start, percentage and amounts |
| `waitlist.csv` | Waitlisted enrolments and their position |

The columns and their order follow the sample data pack README.

## Edge cases from the brief

| Edge case | Where it is tested |
|---|---|
| Percentile exactly 95.00 (STD-0009) | `tests/test_sample_data.py`, `tests/test_engine_scores.py` |
| Section score exactly at the 30% cut-off (STD-0164) | `tests/test_scoring.py`, `tests/test_engine_scores.py` |
| Enrolment on the 15th day after results (ENR-0136) | `tests/test_waiver_window.py`, `tests/test_engine_enrol.py` |
| STAR batch full for a 75% waiver student (ENR-0045) | `tests/test_allocation.py`, `tests/test_engine_enrol.py` |
| Batch with exactly 20 confirmed students (BAT-14) | `tests/test_viability.py`, `tests/test_engine_allocation.py` |
| Refund request on the 15th day after start (ENR-0049) | `tests/test_refunds.py`, `tests/test_engine_refunds.py` |
| Waiver 90% plus sibling 10%, capped at 90% (ENR-0008) | `tests/test_fees.py`, `tests/test_engine_enrol.py` |
| Suspension at exactly 30 days overdue on the day a payment arrives (ENR-0001) | `tests/test_ledger.py`, `tests/test_engine_billing.py` |

## Project structure

```
src/
  scoring/      marks, section cut-offs, percentile, waiver bands, enrolment window
  allocation/   batch filter, STAR rule, capacity, waitlist, viability and merge
  billing/      fees, instalment schedule, payment ledger, late fee, suspension, changes, referral
  refunds/      refund ladder, material rule, waiver forfeiture
  events/       command file parser
  reports/      CSV writer
  engine.py     validates and runs the commands and keeps the state
  main.py       entry point and run summary
tests/          one test module per area, plus checks against the sample pack
data/           sample data pack
docs/           design document and decision log
```

## Documents

- Design document with the business rule register (BR-01 to BR-36): `docs/design.pdf`
- Decision log: `docs/decision_log.md`

## Known limitations

- The stretch goals (hostel bundling, performance-based waiver revision) are not implemented.

## Demo video

Link: https://drive.google.com/file/d/1olf6NyHbwP7uBKyYoC19_U2uTWmX8jMO/view?usp=sharing