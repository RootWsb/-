#!/usr/bin/env python3
"""Build real incremental SkillRouter training data from audit and outcome logs."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from core.router_experience import (  # noqa: E402
    experience_from_route_record,
    index_outcomes,
    load_jsonl,
    match_outcome,
    save_jsonl,
)


REDACTED_TEXT_KEYS = (
    "user_message_redacted",
    "redacted_user_message",
    "query_text_redacted",
    "redacted_query_text",
    "request_summary",
    "notes_redacted",
)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_jsonl(rows: Iterable[Dict[str, Any]], path: Path) -> None:
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


def first_text(row: Dict[str, Any], allow_raw_user_message: bool) -> str:
    for key in REDACTED_TEXT_KEYS:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:8000]
    if allow_raw_user_message:
        value = row.get("user_message")
        if isinstance(value, str) and value.strip():
            return value.strip()[:8000]
    return ""


def prepare_route_record(row: Dict[str, Any], allow_raw_user_message: bool) -> Dict[str, Any]:
    item = dict(row)
    text = first_text(item, allow_raw_user_message)
    if text and not item.get("user_message_redacted"):
        item["user_message_redacted"] = text
    return item


def real_sample_weight(experience: Dict[str, Any]) -> float:
    label_source = experience.get("label_source")
    confidence = experience.get("confidence")
    reward = experience.get("reward")

    if label_source == "human_corrected_skills":
        base = 1.0
    elif label_source == "partial_with_corrections":
        base = 0.85
    elif label_source == "successful_route":
        base = 0.75
    else:
        base = {"high": 0.9, "medium": 0.6, "low": 0.0}.get(confidence, 0.0)

    if reward is not None and float(reward) < 0:
        base = max(base, 0.8)
    return round(min(1.0, max(0.0, base)), 3)


def training_row_from_experience(
    experience: Dict[str, Any],
    skill_index: Dict[str, int],
    min_weight: float,
) -> Optional[Dict[str, Any]]:
    text = str(experience.get("user_message_redacted") or "").strip()
    target = [skill for skill in experience.get("learning_target_skills") or [] if skill in skill_index]
    if not text or not target:
        return None

    weight = real_sample_weight(experience)
    if weight < min_weight:
        return None

    reward = experience.get("reward")
    score = 0.5
    if reward is not None:
        score = max(0.0, min(1.0, (float(reward) + 1.0) / 2.0))

    return {
        "user_message": text,
        "ideal_skills": target,
        "skill_labels": labels_for(target, skill_index),
        "score": round(score, 4),
        "token_efficiency": 0.0,
        "data_source": "real_router_experience",
        "sample_weight": weight,
        "reward": reward,
        "label_source": experience.get("label_source", ""),
        "confidence": experience.get("confidence", ""),
        "request_id": experience.get("request_id", ""),
        "task_id": experience.get("task_id", ""),
        "query_sha256": experience.get("query_sha256", ""),
    }


def build_incremental_rows(
    audit_rows: List[Dict[str, Any]],
    outcome_rows: List[Dict[str, Any]],
    skill_index: Dict[str, int],
    min_weight: float,
    allow_raw_user_message: bool,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    outcomes = index_outcomes(outcome_rows)
    experiences = []
    training_rows = []
    matched = 0

    for row in audit_rows:
        route = prepare_route_record(row, allow_raw_user_message)
        outcome = match_outcome(route, outcomes)
        matched += int(outcome is not None)
        experience = experience_from_route_record(route, outcome).to_dict()
        experiences.append(experience)
        train_row = training_row_from_experience(experience, skill_index, min_weight)
        if train_row:
            training_rows.append(train_row)

    return experiences, training_rows, matched


def main() -> None:
    parser = argparse.ArgumentParser(description="Build real incremental SkillRouter training data.")
    parser.add_argument("--audit", required=True, help="Router audit JSONL.")
    parser.add_argument("--outcomes", default="", help="Outcome JSONL keyed by request_id/query_sha256/task_id.")
    parser.add_argument("--skill-index", default=str(PACKAGE_ROOT / "data_prod" / "skill_index.json"))
    parser.add_argument("--experience-output", default=str(PACKAGE_ROOT / "runtime" / "router_experience.jsonl"))
    parser.add_argument("--training-output", default=str(PACKAGE_ROOT / "runtime" / "training_data_real_incremental.jsonl"))
    parser.add_argument("--min-weight", type=float, default=0.5)
    parser.add_argument(
        "--allow-raw-user-message",
        action="store_true",
        help="Use raw user_message when no redacted text is available. Only use after upstream redaction review.",
    )
    args = parser.parse_args()

    skill_index = load_json(Path(args.skill_index))
    audit_rows = load_jsonl(Path(args.audit))
    outcome_rows = load_jsonl(Path(args.outcomes)) if args.outcomes else []
    experiences, training_rows, matched = build_incremental_rows(
        audit_rows=audit_rows,
        outcome_rows=outcome_rows,
        skill_index=skill_index,
        min_weight=args.min_weight,
        allow_raw_user_message=args.allow_raw_user_message,
    )

    save_jsonl(experiences, Path(args.experience_output))
    write_jsonl(training_rows, Path(args.training_output))

    skipped_no_text = sum(1 for row in experiences if not row.get("user_message_redacted"))
    skipped_no_target = sum(1 for row in experiences if not row.get("learning_target_skills"))
    label_source = Counter(row.get("label_source", "") for row in training_rows)
    confidence = Counter(row.get("confidence", "") for row in training_rows)

    print(f"audit_rows: {len(audit_rows)}")
    print(f"outcome_rows: {len(outcome_rows)}")
    print(f"matched_outcomes: {matched}")
    print(f"experiences: {len(experiences)}")
    print(f"training_rows: {len(training_rows)}")
    print(f"skipped_no_text: {skipped_no_text}")
    print(f"skipped_no_target: {skipped_no_target}")
    print(f"label_source: {dict(label_source)}")
    print(f"confidence: {dict(confidence)}")
    print(f"experience_output: {args.experience_output}")
    print(f"training_output: {args.training_output}")


if __name__ == "__main__":
    main()
