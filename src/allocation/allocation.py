STAR_MIN_WAIVER = 50


def matching_batches(batches, course_id, centre_id, medium, timing):
    return [
        b
        for b in batches.values()
        if b.course_id == course_id
        and b.centre_id == centre_id
        and b.medium == medium
        and b.timing == timing
    ]


def earliest_with_seats(options):
    open_batches = [b for b in options if b.seats_left > 0]
    return min(open_batches, key=lambda b: (b.start_date, b.batch_id), default=None)


def choose_batch(batches, course_id, centre_id, medium, timing, waiver_pct):
    options = matching_batches(batches, course_id, centre_id, medium, timing)
    if waiver_pct >= STAR_MIN_WAIVER:
        star = earliest_with_seats([b for b in options if b.is_star])
        if star:
            return star
    return earliest_with_seats([b for b in options if not b.is_star])


def seat_student(batch, enrol_id):
    batch.confirmed += 1
    batch.students.append(enrol_id)