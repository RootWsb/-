#!/usr/bin/env python3
"""Build router_experience.jsonl from SkillRouter audit and optional outcomes."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from core.router_experience import (  # noqa: E402
    experience_from_route_record,
    index_outcomes,
    load_jsonl,
    match_outcome,
    save_jsonl,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SkillRouter evolution experience records.")
    parser.add_argument(
        "--audit",
        required=True,
        help="Router sidecar/plugin audit JSONL, for example runtime/router_shadow_audit.jsonl.",
    )
    parser.add_argument(
        "--outcomes",
        default="",
        help="Optional JSONL keyed by request_id/query_sha256/task_id with task outcome signals.",
    )
    parser.add_argument(
        "--output",
        default=str(PACKAGE_ROOT / "runtime" / "router_experience.jsonl"),
        help="Output router_experience JSONL.",
    )
    args = parser.parse_args()

    audit_rows = load_jsonl(Path(args.audit))
    outcome_rows = load_jsonl(Path(args.outcomes)) if args.outcomes else []
    outcomes = index_outcomes(outcome_rows)

    experiences = []
    matched = 0
    for row in audit_rows:
        outcome = match_outcome(row, outcomes)
        matched += int(outcome is not None)
        experiences.append(experience_from_route_record(row, outcome).to_dict())

    save_jsonl(experiences, Path(args.output))

    rewards = [row["reward"] for row in experiences if row.get("reward") is not None]
    confidence = Counter(row.get("confidence") for row in experiences)
    labels = Counter(row.get("label_source") for row in experiences)

    print(f"audit_rows: {len(audit_rows)}")
    print(f"outcome_rows: {len(outcome_rows)}")
    print(f"matched_outcomes: {matched}")
    print(f"experiences: {len(experiences)}")
    print(f"rewarded: {len(rewards)}")
    if rewards:
        print(f"avg_reward: {sum(rewards) / len(rewards):.3f}")
    print(f"confidence: {dict(confidence)}")
    print(f"label_source: {dict(labels)}")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()
