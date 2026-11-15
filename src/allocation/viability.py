MIN_CONFIRMED = 20


def is_viable(batch):
    return batch.confirmed >= MIN_CONFIRMED


def merge_target(batches, source):
    candidates = [
        b
        for b in batches.values()
        if b is not source
        and b.course_id == source.course_id
        and b.centre_id == source.centre_id
        and b.medium == source.medium
    ]
    return min(
        candidates,
        key=lambda b: (abs((b.start_date - source.start_date).days), b.start_date, b.batch_id),
        default=None,
    )


def merge_batch(batches, source):
    target = merge_target(batches, source)
    if target is None:
        return None
    moved = list(source.students)
    target.confirmed += source.confirmed
    target.students.extend(moved)
    source.confirmed = 0
    source.students = []
    return target, moved


def check_viability(batches, batch_id):
    source = batches[batch_id]
    if is_viable(source):
        return None
    return merge_batch(batches, source)