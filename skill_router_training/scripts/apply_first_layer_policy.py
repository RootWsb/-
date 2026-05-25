#!/usr/bin/env python3
"""
Apply a first-layer routing policy to ML SkillRouter output.

This is a post-processing experiment:
- remove internal/runtime skills that should not be user-request routing outputs
- force business-critical skills from simple keyword rules
- recompute selection_score and token_waste_ratio against existing labels
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Set

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))


def load_jsonl(path: Path) -> List[Dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def save_jsonl(rows: List[Dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_policy(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def score_selection(selected_skills: List[str], ideal_skills: List[str]) -> Dict:
    selected_set = set(selected_skills)
    ideal_set = set(ideal_skills)

    if ideal_set:
        precision = len(selected_set & ideal_set) / max(1, len(selected_set))
        recall = len(selected_set & ideal_set) / len(ideal_set)
        selection_score = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
    else:
        selection_score = 1.0 if not selected_set else max(0.0, 1.0 - 0.15 * len(selected_set))

    unnecessary = selected_set - ideal_set
    token_waste_ratio = len(unnecessary) / max(1, len(selected_set))
    return {
        "selection_score": round(selection_score, 3),
        "token_waste_ratio": round(token_waste_ratio, 3),
    }


def apply_policy(row: Dict, policy: Dict) -> Dict:
    text = row.get("user_message", "")
    selected: Set[str] = set(row.get("selected_skills") or [])
    removed = []
    forced = []

    excluded = set(policy.get("excluded_skills") or [])
    for skill in sorted(selected & excluded):
        selected.remove(skill)
        removed.append(skill)

    for rule in policy.get("force_rules") or []:
        skill = rule.get("skill")
        keywords = rule.get("any_keywords") or []
        if skill and any(keyword in text for keyword in keywords):
            if skill not in selected:
                forced.append(skill)
            selected.add(skill)

    ordered = [
        "requirements-clarifier",
        "materials-to-problems",
        "wanxiangoa-api",
        "writing-plans",
        "test-driven-development",
        "systematic-debugging",
        "requirements-to-test-cases",
        "test-cases-to-execution-json",
        "execute-test-cases",
        "pm-workflow-router",
        "nocobase-dev-setup",
        "playwright-cli",
        "send-file",
    ]
    selected_list = [skill for skill in ordered if skill in selected]
    selected_list.extend(sorted(selected - set(selected_list)))

    metrics = score_selection(selected_list, row.get("ideal_skills") or [])
    return {
        **row,
        "selected_skills": selected_list,
        "selection_score": metrics["selection_score"],
        "token_waste_ratio": metrics["token_waste_ratio"],
        "policy_removed_skills": removed,
        "policy_forced_skills": forced,
        "generation_method": "ml_skillrouter_policy",
    }


def main():
    parser = argparse.ArgumentParser(description="Apply first-layer routing policy.")
    parser.add_argument(
        "--input",
        default=str(PACKAGE_ROOT / "data" / "ml_tianleixia_log_silver.jsonl"),
    )
    parser.add_argument(
        "--output",
        default=str(PACKAGE_ROOT / "data" / "ml_tianleixia_log_silver_policy.jsonl"),
    )
    parser.add_argument(
        "--policy",
        default=str(PACKAGE_ROOT / "data" / "first_layer_routing_policy.json"),
    )
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    policy = load_policy(Path(args.policy))
    adjusted = [apply_policy(row, policy) for row in rows]
    save_jsonl(adjusted, Path(args.output))

    avg_score = sum(row["selection_score"] for row in adjusted) / len(adjusted) if adjusted else 0
    avg_waste = sum(row["token_waste_ratio"] for row in adjusted) / len(adjusted) if adjusted else 0
    avg_selected = sum(len(row["selected_skills"]) for row in adjusted) / len(adjusted) if adjusted else 0
    print(f"rows: {len(adjusted)}")
    print(f"avg_selection_score: {avg_score:.3f}")
    print(f"avg_token_waste_ratio: {avg_waste:.3f}")
    print(f"avg_selected_skills: {avg_selected:.3f}")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()
