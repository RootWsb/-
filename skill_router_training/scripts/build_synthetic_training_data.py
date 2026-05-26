#!/usr/bin/env python3
"""Build weighted SkillRouter training rows from synthetic router experience."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def save_jsonl(rows: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def labels_for(skills: Iterable[str], skill_index: Dict[str, int]) -> List[int]:
    labels = [0] * len(skill_index)
    for skill in skills:
        if skill in skill_index:
            labels[skill_index[skill]] = 1
    return labels


def weight_for(row: Dict[str, Any]) -> float:
    confidence = row.get("confidence")
    scenario = row.get("scenario_type")
    reward = row.get("reward")
    base = {"high": 0.5, "medium": 0.3, "low": 0.0}.get(confidence, 0.0)
    if scenario in {"missing_key_skill", "unnecessary_skill", "failure"}:
        base += 0.15
    if reward is not None and reward < 0:
        base += 0.05
    return round(min(base, 0.7), 3)


def build_rows(experiences: List[Dict[str, Any]], skill_index: Dict[str, int], min_weight: float) -> List[Dict[str, Any]]:
    rows = []
    for item in experiences:
        target = item.get("learning_target_skills") or item.get("ideal_skills") or []
        target = [skill for skill in target if skill in skill_index]
        if not target:
            continue
        weight = weight_for(item)
        if weight < min_weight:
            continue
        rows.append(
            {
                "user_message": item.get("user_message", ""),
                "ideal_skills": target,
                "skill_labels": labels_for(target, skill_index),
                "score": max(0.0, min(1.0, (float(item.get("reward") or 0.0) + 1.0) / 2.0)),
                "token_efficiency": 0.0,
                "data_source": "synthetic_router_experience",
                "sample_weight": weight,
                "reward": item.get("reward"),
                "scenario_type": item.get("scenario_type", ""),
                "confidence": item.get("confidence", ""),
                "label_source": item.get("label_source", ""),
                "request_id": item.get("request_id", ""),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build weighted training rows from synthetic router experience.")
    parser.add_argument("--experience", default=str(PACKAGE_ROOT / "data_prod" / "synthetic_router_experience_1000.jsonl"))
    parser.add_argument("--skill-index", default=str(PACKAGE_ROOT / "data_prod" / "skill_index.json"))
    parser.add_argument("--output", default=str(PACKAGE_ROOT / "data_prod" / "synthetic_training_data_1000.jsonl"))
    parser.add_argument("--min-weight", type=float, default=0.1)
    args = parser.parse_args()

    skill_index = load_json(Path(args.skill_index))
    experiences = load_jsonl(Path(args.experience))
    rows = build_rows(experiences, skill_index, args.min_weight)
    save_jsonl(rows, Path(args.output))

    scenario = Counter(row.get("scenario_type") for row in rows)
    confidence = Counter(row.get("confidence") for row in rows)
    skill_counts = Counter()
    for row in rows:
        skill_counts.update(row.get("ideal_skills") or [])

    print(f"experience_rows: {len(experiences)}")
    print(f"training_rows: {len(rows)}")
    print(f"avg_sample_weight: {sum(row['sample_weight'] for row in rows) / max(1, len(rows)):.3f}")
    print(f"scenario: {dict(scenario)}")
    print(f"confidence: {dict(confidence)}")
    print(f"top_skills: {skill_counts.most_common(12)}")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()
