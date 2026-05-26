import json
import tempfile
import unittest
from pathlib import Path

from skill_router_training.core.router_experience import (
    RouterOutcome,
    compute_reward,
    derive_learning_target,
    experience_from_route_record,
    index_outcomes,
    load_jsonl,
    match_outcome,
    save_jsonl,
)


class RouterExperienceTest(unittest.TestCase):
    def test_successful_smaller_route_gets_positive_reward(self):
        outcome = RouterOutcome(status="success", user_accepted=True)

        reward = compute_reward(
            selected_skills=["plugin-dev"],
            baseline_skills=["plugin-dev", "debugging", "planning"],
            outcome=outcome,
        )

        self.assertGreater(reward, 0.9)

    def test_missing_key_skill_penalizes_reward(self):
        outcome = RouterOutcome(status="partial", missing_skills=["test-driven-development"])

        reward = compute_reward(
            selected_skills=["plugin-dev"],
            baseline_skills=["plugin-dev"],
            outcome=outcome,
        )

        self.assertLess(reward, 0.1)

    def test_no_outcome_signal_keeps_reward_empty(self):
        self.assertIsNone(
            compute_reward(
                selected_skills=["plugin-dev"],
                baseline_skills=[],
                outcome=RouterOutcome(),
            )
        )

    def test_human_corrections_become_high_confidence_target(self):
        target, source, confidence = derive_learning_target(
            selected_skills=["plugin-dev"],
            outcome=RouterOutcome(human_corrected_skills=["plugin-dev", "debugging"]),
        )

        self.assertEqual(target, ["plugin-dev", "debugging"])
        self.assertEqual(source, "human_corrected_skills")
        self.assertEqual(confidence, "high")

    def test_builds_experience_from_shadow_audit_and_outcome(self):
        route = {
            "request_id": "req-1",
            "query_sha256": "abc",
            "selected_skills": [
                {"skill_name": "plugin-dev", "score": 0.9},
                {"skill_name": "debugging", "score": 0.7},
            ],
            "shadow_comparison": {"baseline_skills": ["plugin-dev", "planning"]},
            "threshold": 0.5,
            "top_k": 8,
        }
        outcome = {
            "request_id": "req-1",
            "status": "success",
            "unnecessary_skills": ["debugging"],
        }

        experience = experience_from_route_record(route, outcome).to_dict()

        self.assertEqual(experience["request_id"], "req-1")
        self.assertEqual(experience["baseline_skills"], ["plugin-dev", "planning"])
        self.assertEqual(experience["router_selected_skills"], ["plugin-dev", "debugging"])
        self.assertEqual(experience["scores"], {"plugin-dev": 0.9, "debugging": 0.7})
        self.assertEqual(experience["learning_target_skills"], ["plugin-dev"])
        self.assertIsNotNone(experience["reward"])

    def test_outcomes_can_match_by_request_id_or_hash(self):
        outcomes = index_outcomes([
            {"request_id": "req-1", "status": "success"},
            {"query_sha256": "hash-2", "status": "failure"},
        ])

        self.assertEqual(match_outcome({"request_id": "req-1"}, outcomes)["status"], "success")
        self.assertEqual(match_outcome({"query_sha256": "hash-2"}, outcomes)["status"], "failure")

    def test_jsonl_helpers_round_trip(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "records.jsonl"
            save_jsonl([{"a": 1}, {"b": 2}], path)

            self.assertEqual(load_jsonl(path), [{"a": 1}, {"b": 2}])
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
