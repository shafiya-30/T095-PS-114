# Decision Log

1. Percentile is 100 x (students in the same test with total <= yours) / cohort size, rounded to 2 decimals, so students with equal totals share one percentile (sample README).
2. The waiver band is chosen from the rounded percentile, so 94.996 becomes 95.00 and gets the 75% band.
3. A section passes with a score of 24 or more (30% of 80), so exactly 24 passes.
4. A failed section cut-off caps the waiver at 25% whatever the percentile band is.
5. Every test is scored at start-up and the better waiver across attempts applies, because the sample README places a re-test student in a STAR batch before the re-test result date.
6. The 15-day enrolment window is counted from the earliest published result; day 15 keeps the waiver and day 16 forfeits it.
7. The batch start date is day 0 for the refund ladder, so day 15 gets 75% and day 16 gets 50%.
8. Only waiver 50% or more can take a STAR seat; when STAR is full the student goes to the earliest REGULAR batch with space and keeps the waiver.
9. A batch with exactly 20 confirmed students is viable; below 20 it merges into the batch with the same course, centre and medium that has the nearest start date, ties going to the earlier start.
10. Merged students are listed under the batch they were merged out of with status MERGED, and a request within 7 days of the notice gets a full refund with no waiver forfeiture.
11. Money uses Decimal rounded to 2 places (half up); instalments are equal shares and the last one absorbs the rounding difference.
12. GST of 18% applies to tuition, material, exam series and the processing fee; late fees and transfer charges carry no GST.
13. The late fee is Rs 100 per day after a 10-day grace period, capped at Rs 3,000, and it stops growing on the day the instalment is paid.
14. A payment on exactly day 30 overdue clears the instalment before suspension applies, so the student is ACTIVE.
15. A payment goes to the earliest unsettled instalment, covering the late fee first and then the instalment amount, and any surplus moves to the next instalment.
16. The refund base is the tuition of settled instalments (already net of waiver); material is refunded in full only if unopened and within day 15; GST is refunded on the refunded tuition and material.
17. The refund clock always counts from the batch the student was first allocated to, so transfers and upgrades never reset it.
18. A STAR dropout on days 0 to 15 after start forfeits the waiver for any enrolment within 365 days; dropping out before the start does not.
19. Waitlisted students get no fee statement, their position is counted among those with the same preferences, and a freed seat goes to the first in line.
20. A transfer needs the same course; the first same-centre transfer is free and any other costs Rs 2,500; extra charges are stored on the enrolment but not yet shown on fee statements.
21. A command with an unknown student, course, centre, batch, test or enrolment, a bad date, amount or plan, or the wrong number of arguments is skipped with a reason and its line number, and the run continues.
22. A payment to a dropped or waitlisted enrolment, and a repeated payment id, is rejected instead of being applied.
23. When a dropout or transfer frees a seat, the first waitlisted student with a matching preference takes it (a STAR seat only for waiver 50% or more), and that student's billing starts on that day.
24. A suspension runs from day 30 overdue until the instalment is paid; overlapping overdue instalments count as one suspension, and a student with two suspensions cannot choose the 4-instalment plan.
25. A waitlisted student who drops out is removed from the waitlist with no refund, because nothing was paid.