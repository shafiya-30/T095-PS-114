# PS-114 – Coaching Institute Batch Allocation, Scholarship Test and Refund Policy Engine — Sample Data Pack

Prepared by 10 SECONDS for Team T095.

## Files

| File | What it holds | Row count |
|---|---|---|
| `courses.csv` | 5 courses with tuition, material, exam-series fee and GST | 5 data rows |
| `centres.csv` | 3 centres | 3 data rows |
| `batches.csv` | 18 batches with course, centre, medium, timing, STAR/REGULAR, start date, capacity and seats already confirmed from earlier admission rounds | 18 data rows |
| `answer_key.csv` | Answer key for the scholarship test SCH-01 and the re-test SCH-02 (60 questions each, 3 sections of 20) | 120 data rows |
| `students.csv` | 180 test candidates with sibling and referral links | 180 data rows |
| `test_responses.csv` | 200 responses: 180 for SCH-01 and 20 re-test responses for SCH-02 | 200 data rows |
| `commands.txt` | Result publication, 150 enrolments, 18 viability checks, ~60 dropout/transfer/upgrade/payment events and print requests | 396 command lines (excluding comments) |

Row numbers quoted below are 1-based data-row numbers (the header is row 0). Line numbers for `commands.txt` are physical line numbers including comment lines.

## Column reference

Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 means 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix. An empty cell means "not applicable" and is only allowed where the notes say so.

### `courses.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| course_id | string | — | JEE-2Y, JEE-1Y, NEET-1Y, NEET-2Y, FOUND-1Y | — |
| course_name | string | — | — | — |
| duration_months | int | months | — | — |
| tuition_fee | decimal | Rs | — | waiver and sibling discount apply to this only |
| material_fee | decimal | Rs | — | — |
| exam_series_fee | decimal | Rs | — | — |
| gst_pct | decimal | % | — | on every charge |

### `centres.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| centre_id | string | CTR-nn | — | — |
| centre_name | string | — | — | — |
| city | string | — | — | — |

### `batches.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| batch_id | string | BAT-nn | — | — |
| course_id | string | — | courses.csv | — |
| centre_id | string | — | centres.csv | — |
| medium | enum | — | ENGLISH, KANNADA | — |
| timing | enum | — | MORNING, EVENING, WEEKEND | — |
| batch_type | enum | — | STAR, REGULAR | STAR seats are for waiver >= 50% |
| start_date | date | — | — | refund clock starts here |
| capacity | int | seats | 60 | — |
| seats_already_confirmed | int | seats | — | confirmed before this pack (count towards capacity and the 20-student viability check) |

### `answer_key.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| test_id | string | SCH-nn | SCH-01, SCH-02 | — |
| question_no | int | — | 1-60 | — |
| section | enum | — | PHY (1-20), CHE (21-40), APT (41-60) | section max 80 marks |
| correct_option | enum | — | A, B, C, D | — |

### `students.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| student_id | string | STD-nnnn | — | — |
| student_name | string | — | — | — |
| gender | enum | — | M, F | — |
| dob | date | — | — | — |
| mobile | string | 10 digits | — | — |
| city | string | — | — | — |
| sibling_of | string | — | students.csv | empty = no sibling; 10% sibling discount on tuition |
| referred_by | string | — | students.csv | empty = not referred |

### `test_responses.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| response_id | string | RSP-nnnn | — | — |
| test_id | string | — | answer_key.csv | cohort for percentile |
| student_id | string | — | students.csv | — |
| submitted_ts | timestamp | — | — | — |
| answers | string | 60 chars | A, B, C, D or - per question | character n = question n; - = unattempted |

## Command file format

`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands must be processed strictly in file order. Lines starting with `#` are comments and blank lines are ignored. An argument written as `-` means "not applicable". Every command used in this pack:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| `PUBLISH_RESULT` | `test_id|result_date` | Score the cohort; the 15-day enrolment window starts on result_date |
| `PRINT_SCORES` | `test_id` | — |
| `ENROL` | `enrol_id|student_id|enrol_date|course_id|centre_id|medium|timing|plan` | plan 1, 2 or 4 instalments; instalment 1 is paid with this command |
| `VIABILITY_CHECK` | `batch_id|check_date` | 7 days before start: merge if fewer than 20 confirmed |
| `PRINT_ALLOCATION` | `batch_id` | Allocation list after the check |
| `DROPOUT` | `enrol_id|request_date|material_unopened` | Refund request; material_unopened true/false |
| `TRANSFER` | `enrol_id|date|to_batch_id` | — |
| `UPGRADE` | `enrol_id|date|new_course_id|new_batch_id` | Upgrade or downgrade of course |
| `PAYMENT` | `payment_id|enrol_id|payment_date|amount|mode` | Later instalments (incl. any late fee paid) |
| `PRINT_FEE_STATEMENT` | `enrol_id|as_of_date` | — |
| `PRINT_WAITLIST` | `as_of_date` | — |
| `PRINT_REFUND_ORDERS` | `from_date|to_date` | — |

## Planted scenarios

Every edge case in the brief, mapped to the exact record where it occurs, followed by extra traps.

- **EC-01 Percentile exactly 95.00**
  - STD-0009: SCH-01 total 158 — exactly 171 of 180 candidates score at or below it, percentile = 100 x 171 / 180 = 95.00 -> 75% band (all sections >= 24) — `test_responses.csv row 32`
- **EC-02 Section score exactly at the 30% cut-off**
  - STD-0164: SCH-01 CHE section score exactly 24 (= 30% of 80, 6 correct, 0 wrong) — meets the cut-off, so the percentile band (75%) is NOT capped — `test_responses.csv row 44`
- **EC-03 Enrolment on the 15th day after results**
  - STD-0095 (50% waiver): results published 2026-03-25, ENROL on 2026-04-09 = 15th day — within the window, waiver kept (STAR BAT-04) — `commands.txt line 141`
- **EC-04 STAR batch full for a 75% waiver student**
  - STAR batch BAT-07 (CTR-02 JEE-2Y ENGLISH MORNING) starts with 58 seats confirmed; STD-0053 and STD-0079 (waiver >= 50%) fill it to 60; STD-0090 (75% waiver, same preference) finds STAR full and goes to the earliest-starting matching REGULAR batch BAT-08 (keeps the 75% waiver) — `commands.txt lines 19, 30 and commands.txt line 48`
- **EC-05 Batch with exactly 20 confirmed students at the 7-day mark**
  - BAT-14 (CTR-03 JEE-2Y KANNADA EVENING, start 2026-05-04): 14 seats already confirmed + 6 enrolments = exactly 20 confirmed at the 7-day check on 2026-04-27 — viable, NOT merged — `enrolments commands.txt lines 65, 94, 130, 146, 148, 160; check commands.txt line 179`
- **EC-06 Refund request on the 15th day after batch start**
  - ENR-0049 in BAT-13 (start 2026-04-27) requests a refund on 2026-05-12 = 15th day after start — 75% of tuition paid (net of waiver); material unopened and within 15 days, so material refundable; GST refunded proportionally — `commands.txt line 199`
- **EC-07 Waiver 90% plus sibling 10% (cap)**
  - STD-0153: SCH-01 topper (percentile 100.00, 90% waiver) and sibling of STD-0001 — 90% + 10% = 100% is capped at 90% on tuition — `students.csv row 153`
- **EC-08 Suspension at exactly 30 days overdue on the day a payment arrives**
  - ENR-0001 (plan 2): 2nd instalment due 2026-05-25; payment arrives on 2026-06-24 = exactly 30 days overdue, the same day test access would be suspended — late fee 20 days x Rs 100 = Rs 2000.00 included in the amount — `commands.txt line 241`
- **Extra traps (not in the brief, but realistic):**
  - STD-0026: SCH-01 APT section score 23 (one mark under the cut-off) at percentile 97.78 — waiver capped at 25% — `test_responses.csv row 12`
  - Re-test: STD-0096 scores 25% on SCH-01 and 90% on SCH-02 (percentile 100.00 in the 20-candidate re-test cohort) — the better (90%) applies; STD-0073 gets 25% then 0% — keeps 25% — `test_responses.csv row 147; SCH-02 rows for both`
  - Tie: STD-0070 and STD-0133 both total 153 on SCH-01 — identical percentile (93.33), no tie-break by time — `test_responses.csv row 176`
  - BAT-11 (CTR-02 NEET-1Y ENGLISH MORNING, start 2026-05-18): 13 + 6 = 19 confirmed at the 2026-05-11 check — merged into the nearest same-centre, same-medium batch BAT-10 (NEET-1Y, start 2026-05-04); merged students may take a FULL refund within 7 days of the merge notice — `enrolments commands.txt lines 45, 78, 107, 137, 147, 157; check commands.txt line 197`
  - BAT-15 (CTR-03 NEET-1Y ENGLISH MORNING) has 59 seats confirmed: ENR-0069 takes seat 60, ENR-0080 is WAITLISTED (no other matching batch) — `commands.txt lines 74, 85`
  - STD-0015 (50% waiver) enrols on 2026-04-10 = 16th day after results — waiver FORFEITED (0%), billed full tuition — `commands.txt line 145`
  - STD-0026 (capped at 25%) prefers JEE-2Y ENGLISH EVENING at CTR-01 — a REGULAR batch; STD-0164 (75%) gets STAR BAT-01 — `commands.txt lines 12, 15`
  - ENR-0042 (merged out of BAT-11 on 2026-05-11) drops on 2026-05-15 — within 7 days of the merge notice: FULL refund — `commands.txt line 201`
  - ENR-0012 in BAT-02 (start 2026-04-27) drops on 2026-05-13 = day 16 — 50% band, and the material is NOT refundable even though unopened (only within 15 days) — `commands.txt line 200`
  - ENR-0038 in BAT-05 (start 2026-05-04) drops before the batch starts — 90% of tuition paid — `commands.txt line 175`
  - ENR-0035 in BAT-01 (start 2026-04-20) drops on 2026-06-22 = day 63 — nil refund — `commands.txt line 239`
  - ENR-0019 (STAR BAT-17, start 2026-04-20) drops on 2026-04-28 = day 8 — 75% of net tuition paid; as a STAR dropout within 15 days the waiver value is also forfeited for any re-enrolment within 1 year — `commands.txt line 186`
  - TRANSFER ENR-0057 BAT-13 -> BAT-14 (same centre CTR-03, same course) — free (first transfer) — `commands.txt line 195`
  - TRANSFER ENR-0020 BAT-02 (CTR-01) -> BAT-08 (CTR-02) — Rs 2500.00 charge; the later DROPOUT on 2026-05-20 is day 23 from the ORIGINAL start 2026-04-27 (50%), not day 9 from BAT-08's start — `commands.txt lines 187, 202`
  - UPGRADE ENR-0026 NEET-1Y (BAT-04, STAR) -> NEET-2Y (BAT-05) — tuition difference billed, waiver % (75%) carries over — `commands.txt line 188`
  - Downgrade ENR-0040 JEE-2Y -> JEE-1Y on 2026-04-22, before BAT-02 starts — allowed, 10% of the difference charged; downgrade ENR-0059 on 2026-05-06 after BAT-13 started — REJECTED — `commands.txt lines 174, 196`
  - Two dropouts 33 and 40 days after their batch start — 31–60 day band, 25% of net tuition paid — `commands.txt lines 229, 234`
  - STD-0089 (referred by STD-0001) pays the 2nd instalment of ENR-0005 — Rs 5000.00 referral credit to STD-0001 from that date — `commands.txt line 219; students.csv row 89`

## What is NOT in this pack

Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation

Produce these CSV files (header row, same conventions as above, rows sorted as stated). Where the brief is silent on a format detail the choice below is binding for evaluation.

### `scores.csv`

One row per response per PRINT_SCORES, ordered by total desc then student_id.

Columns, in order: `test_id`, `student_id`, `phy`, `che`, `apt`, `total`, `percentile`, `cutoff_passed`, `waiver_pct`

### `allocations.csv`

One row per student per PRINT_ALLOCATION (pack enrolments only).

Columns, in order: `batch_id`, `enrol_id`, `student_id`, `waiver_pct`, `status`

### `fee_statements.csv`

One row per instalment per PRINT_FEE_STATEMENT.

Columns, in order: `enrol_id`, `as_of_date`, `instalment_no`, `due_date`, `tuition`, `material`, `exam_series`, `processing_fee`, `other_charges`, `gst`, `amount`, `paid`, `late_fee`, `balance`, `access_status`

### `refund_orders.csv`

One row per approved refund, ordered by request date.

Columns, in order: `enrol_id`, `request_date`, `days_from_start`, `refund_pct`, `tuition_refund`, `material_refund`, `gst_refund`, `total_refund`, `waiver_forfeited`

### `waitlist.csv`

One row per waitlisted enrolment.

Columns, in order: `as_of_date`, `enrol_id`, `student_id`, `course_id`, `centre_id`, `medium`, `timing`, `position`

Binding choices: percentile = 100 x (number of candidates in the same test_id with total <= yours) / (cohort size), rounded to 2 decimals; section cut-off is score >= 24 (30% of 80). Instalments are equal shares of the total payable (net tuition, material, exam series, processing fee, all + 18% GST), due on enrol_date + 0/60/120/180 days, the last absorbing rounding. Days after batch start are counted with the start date as day 0. `status` ALLOCATED, MERGED, TRANSFERRED, DROPPED or WAITLISTED; `access_status` ACTIVE or SUSPENDED.
