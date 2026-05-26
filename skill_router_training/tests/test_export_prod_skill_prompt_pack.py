import json
import tempfile
import unittest
from pathlib import Path

from skill_router_training.scripts.export_prod_skill_prompt_pack import build_skill_corpus, build_prompts
from skill_router_training.scripts.convert_synthetic_router_records import convert_record


class SkillPromptPackTest(unittest.TestCase):
    def test_builds_corpus_from_skill_files(self):
        with tempfile.TemporaryDirectory() as root:
            skill_dir = Path(root) / "agent" / "skills" / "alpha"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: alpha\ndescription: Use for alpha work\n---\n# Alpha\nDetailed alpha workflow.",
                encoding="utf-8",
            )

            corpus = build_skill_corpus(Path(root), {"alpha": 0, "beta": 1})

            self.assertEqual(len(corpus), 1)
            self.assertEqual(corpus[0]["name"], "alpha")
            self.assertEqual(corpus[0]["description"], "Use for alpha work")
            self.assertEqual(corpus[0]["source_count"], 1)

    def test_prompt_mentions_schema_and_focus_skills(self):
        corpus = [
            {
                "name": "alpha",
                "index": 0,
                "description": "Alpha skill",
                "title": "Alpha",
                "excerpt": "Alpha details",
                "source_count": 1,
                "source_paths": [],
            }
        ]

        prompt = build_prompts(corpus, num_prompts=1, records_per_prompt=3, focus_size=1)[0]["prompt"]

        self.assertIn("Generate exactly 3 JSON objects", prompt)
        self.assertIn("router_selected_skills", prompt)
        self.assertIn("alpha", prompt)

    def test_converts_synthetic_record_to_rewarded_experience(self):
        row = {
            "user_message": "请修复构建失败并补测试",
            "available_skills": ["systematic-debugging", "test-driven-development"],
            "baseline_skills": ["systematic-debugging"],
            "router_selected_skills": ["systematic-debugging"],
            "outcome": {
                "status": "partial",
                "missing_skills": ["test-driven-development"],
            },
            "ideal_skills": ["systematic-debugging", "test-driven-development"],
        }

        experience = convert_record(row, 1, {"systematic-debugging", "test-driven-development"})

        self.assertTrue(experience["synthetic"])
        self.assertEqual(experience["request_id"], "synthetic-000001")
        self.assertEqual(experience["outcome"]["missing_skills"], ["test-driven-development"])
        self.assertIsNotNone(experience["reward"])


if __name__ == "__main__":
    unittest.main()
