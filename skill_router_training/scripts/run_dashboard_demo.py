#!/usr/bin/env python3
"""Run the SkillRouter WebUI with a tiny fake model for local dashboard checks."""

from __future__ import annotations

import argparse
import json
import tempfile
import sys
from pathlib import Path

import uvicorn

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE_ROOT))

from skill_router_training.service.app import RouterRuntime, RouterSettings, create_app


class DemoModel:
    def predict(self, query, skill_names, top_k, threshold):
        scores = [0.97, 0.86, 0.72, 0.48, 0.31]
        return [
            {"skill": skill, "score": scores[index % len(scores)]}
            for index, skill in enumerate(skill_names)
        ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a fake SkillRouter dashboard server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8781)
    parser.add_argument("--dashboard-dir", default="skill_router_training/runtime/dashboard_demo")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tempdir:
        root = Path(tempdir)
        checkpoint = root / "checkpoint"
        checkpoint.mkdir()
        skills = {
            "test-driven-development": 0,
            "systematic-debugging": 1,
            "nocobase-plugin-development": 2,
            "writing-plans": 3,
            "brainstorming": 4,
        }
        (checkpoint / "config.json").write_text(
            json.dumps({"num_skills": len(skills), "embedding_model": "demo"}),
            encoding="utf-8",
        )
        skill_index = root / "skill_index.json"
        skill_index.write_text(json.dumps(skills), encoding="utf-8")

        runtime = RouterRuntime(
            RouterSettings(
                checkpoint=checkpoint,
                skill_index=skill_index,
                device="cpu",
                threshold=0.5,
                top_k=3,
                dashboard_dir=Path(args.dashboard_dir),
            ),
            model=DemoModel(),
        )
        uvicorn.run(create_app(runtime), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
