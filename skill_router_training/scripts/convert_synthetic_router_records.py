#!/usr/bin/env python3
"""Convert LLM-generated synthetic router records into router_experience.v1 JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from core.router_experience import experience_from_route_record, save_jsonl, unique_skills  # noqa: E402


def load_records(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        value = json.loads(stripped)
        if not isinstance(value, list):
            raise ValueError("Top-level JSON array expected.")
        return [row for row in value if isinstance(row, dict)]

    rows = []
    for line in stripped.splitlines():
        line = line.strip()
        if not line:
            continue
        value = json.loads(line)
        if isinstance(value, list):
            rows.extend(row for row in value if isinstance(row, dict))
        elif isinstance(value, dict):
            rows.append(value)
    return rows


def load_skill_names(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8") as handle:
        return set(json.load(handle).keys())


def filter_skills(skills: Iterable[str], allowed: set[str]) -> List[str]:
    return [skill for skill in unique_skills(list(skills)) if skill in allowed]


def convert_record(row: Dict[str, Any], index: int, allowed: set[str]) -> Dict[str, Any]:
    selected = filter_skills(row.get("router_selected_skills") or row.get("selected_skills") or [], allowed)
    baseline = filter_skills(row.get("baseline_skills") or [], allowed)
    available = filter_skills(row.get("available_skills") or list(allowed), allowed)
    outcome = row.get("outcome") if isinstance(row.get("outcome"), dict) else {}
    explicit_human_correction = bool(outcome.get("human_corrected_skills"))
    normalized_outcome = {
        **outcome,
        "missing_skills": filter_skills(outcome.get("missing_skills") or [], allowed),
        "unnecessary_skills": filter_skills(outcome.get("unnecessary_skills") or [], allowed),
        "human_corrected_skills": filter_skills(outcome.get("human_corrected_skills") or [], allowed),
    }
    route = {
        "request_id": str(row.get("request_id") or f"synthetic-{index:06d}"),
        "available_skills": available,
        "baseline_skills": baseline,
        "selected_skill_names": selected,
        "threshold": row.get("threshold"),
        "top_k": row.get("top_k"),
    }
    experience = experience_from_route_record(route, normalized_outcome).to_dict()
    experience["synthetic"] = True
    experience["user_message"] = str(row.get("user_message") or "")[:2000]
    experience["ideal_skills"] = filter_skills(row.get("ideal_skills") or [], allowed)
    if not explicit_human_correction and not experience.get("learning_target_skills"):
        experience["learning_target_skills"] = experience["ideal_skills"]
        experience["label_source"] = "synthetic_ideal_skills"
        experience["confidence"] = "medium" if experience["ideal_skills"] else "low"
    experience["scenario_type"] = str(row.get("scenario_type") or "")
    experience["reason"] = str(row.get("reason") or "")[:500]
    return experience


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert synthetic LLM router records to experience JSONL.")
    parser.add_argument("--input", required=True, help="JSON or JSONL file returned by an external LLM.")
    parser.add_argument("--skill-index", default=str(PACKAGE_ROOT / "data_prod" / "skill_index.json"))
    parser.add_argument("--output", default=str(PACKAGE_ROOT / "data_prod" / "synthetic_router_experience.jsonl"))
    args = parser.parse_args()

    allowed = load_skill_names(Path(args.skill_index))
    rows = load_records(Path(args.input))
    experiences = [convert_record(row, index + 1, allowed) for index, row in enumerate(rows)]
    save_jsonl(experiences, Path(args.output))

    rewarded = sum(1 for row in experiences if row.get("reward") is not None)
    high = sum(1 for row in experiences if row.get("confidence") == "high")
    print(f"input_records: {len(rows)}")
    print(f"experiences: {len(experiences)}")
    print(f"rewarded: {rewarded}")
    print(f"high_confidence: {high}")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()
