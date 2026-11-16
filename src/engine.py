from dataclasses import asdict
from datetime import date
from pathlib import Path

from src.reports.writers import write_csv
from src.scoring.loader import load_answer_keys, load_responses
from src.scoring.scoring import score_cohort

SCORE_COLUMNS = (
    "test_id",
    "student_id",
    "phy",
    "che",
    "apt",
    "total",
    "percentile",
    "cutoff_passed",
    "waiver_pct",
)


class Engine:
    def __init__(self, data_dir):
        data = Path(data_dir)
        self.keys = load_answer_keys(data / "answer_key.csv")
        self.responses = load_responses(data / "test_responses.csv")
        self.result_dates = {}
        self.scores = {}
        self.score_rows = []

    def publish_result(self, test_id, result_date):
        scored = score_cohort(test_id, self.responses[test_id], self.keys[test_id])
        self.scores[test_id] = {s.student_id: s for s in scored}
        self.result_dates[test_id] = date.fromisoformat(result_date)

    def print_scores(self, test_id):
        ordered = sorted(self.scores[test_id].values(), key=lambda s: (-s.total, s.student_id))
        self.score_rows.extend(asdict(s) for s in ordered)

    def execute(self, command):
        if command.name == "PUBLISH_RESULT":
            self.publish_result(*command.args)
        elif command.name == "PRINT_SCORES":
            self.print_scores(*command.args)

    def run(self, commands):
        for command in commands:
            self.execute(command)

    def write_outputs(self, out_dir):
        write_csv(Path(out_dir) / "scores.csv", SCORE_COLUMNS, self.score_rows)