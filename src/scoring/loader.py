import csv
from collections import defaultdict


def load_answer_keys(path):
    keys = defaultdict(dict)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            keys[row["test_id"]][int(row["question_no"])] = row["correct_option"]
    return {test: [q[i] for i in range(1, 61)] for test, q in keys.items()}


def load_responses(path):
    by_test = defaultdict(list)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            by_test[row["test_id"]].append(row)
    return dict(by_test)