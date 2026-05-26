import argparse
import tempfile
import unittest
from pathlib import Path

from skill_router_training.scripts.build_real_incremental_training_data import build_incremental_rows
from skill_router_training.scripts.make_router_release_decision import decide, metrics


class RealIncrementalTrainingDataTest(unittest.TestCase):
    def test_builds_training_rows_only_when_text_and_target_exist(self):
        skill_index = {"systematic-debugging": 0, "writing-plans": 1}
        audit_rows = [
            {
                "request_id": "req-1",
                "user_message_redacted": "请排查插件没有上报事件的问题",
                "selected_skills": ["systematic-debugging", "writing-plans"],
            },
            {
                "request_id": "req-2",
                "selected_skills": ["systematic-debugging"],
            },
        ]
        outcome_rows = [
            {
                "request_id": "req-1",
                "status": "success",
                "unnecessary_skills": ["writing-plans"],
            },
            {"request_id": "req-2", "status": "success"},
        ]

        experiences, training_rows, matched = build_incremental_rows(
            audit_rows=audit_rows,
            outcome_rows=outcome_rows,
            skill_index=skill_index,
            min_weight=0.5,
            allow_raw_user_message=False,
        )

        self.assertEqual(matched, 2)
        self.assertEqual(len(experiences), 2)
        self.assertEqual(len(training_rows), 1)
        self.assertEqual(training_rows[0]["user_message"], "请排查插件没有上报事件的问题")
        self.assertEqual(training_rows[0]["ideal_skills"], ["systematic-debugging"])
        self.assertEqual(training_rows[0]["skill_labels"], [1, 0])
        self.assertEqual(training_rows[0]["data_source"], "real_router_experience")


class RouterReleaseDecisionTest(unittest.TestCase):
    def test_blocks_candidate_with_lower_f1(self):
        current_rows = [
            {"selected_skills": ["a"], "ideal_skills": ["a"], "selection_score": 1.0, "token_waste_ratio": 0.0},
            {"selected_skills": ["b"], "ideal_skills": ["b"], "selection_score": 1.0, "token_waste_ratio": 0.0},
        ]
        candidate_rows = [
            {"selected_skills": ["a", "x"], "ideal_skills": ["a"], "selection_score": 0.67, "token_waste_ratio": 0.5},
            {"selected_skills": ["x"], "ideal_skills": ["b"], "selection_score": 0.0, "token_waste_ratio": 1.0},
        ]
        args = argparse.Namespace(
            min_rows=1,
            min_f1_delta=0.02,
            max_waste_delta=0.03,
            max_missing_delta=0.0,
            max_selected_ratio=1.15,
        )

        decision, reasons = decide(metrics(current_rows), metrics(candidate_rows), args)

        self.assertEqual(decision, "BLOCK_RELEASE_OR_ROLL_BACK")
        self.assertTrue(any("Micro F1" in reason for reason in reasons))


if __name__ == "__main__":
    unittest.main()
