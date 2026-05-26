#!/usr/bin/env python3
"""
Build a small review set for human gold-labeling.

Priority:
1. low-confidence silver labels
2. worst ML samples if ML output is available
3. deterministic spread from the remaining candidates
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))


def load_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        return []
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


def main():
    parser = argparse.ArgumentParser(description="Create gold-label review set.")
    parser.add_argument(
        "--silver",
        default=str(PACKAGE_ROOT / "data" / "tianleixia_log_silver.jsonl"),
    )
    parser.add_argument(
        "--ml",
        default=str(PACKAGE_ROOT / "data" / "ml_tianleixia_log_silver.jsonl"),
    )
    parser.add_argument(
        "--output",
        default=str(PACKAGE_ROOT / "data" / "tianleixia_gold_review_50.jsonl"),
    )
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    silver = load_jsonl(Path(args.silver))
    ml_by_message = {
        row.get("user_message", ""): row
        for row in load_jsonl(Path(args.ml))
    }

    candidates = []
    seen = set()

    def add(row: Dict, reason: str):
        message = row.get("user_message", "")
        if not message or message in seen:
            return
        seen.add(message)
        ml = ml_by_message.get(message, {})
        candidates.append({
            **row,
            "review_reason": reason,
            "ml_selected_skills": ml.get("selected_skills", []),
            "ml_selection_score": ml.get("selection_score"),
            "ml_token_waste_ratio": ml.get("token_waste_ratio"),
            "gold_ideal_skills": row.get("ideal_skills"),
            "gold_notes": "",
        })

    for row in silver:
        if row.get("label_confidence") == "low":
            add(row, "low_confidence_silver_label")

    worst = sorted(
        silver,
        key=lambda row: (
            ml_by_message.get(row.get("user_message", ""), {}).get("selection_score", 1.0),
            -len(row.get("ideal_skills") or []),
        ),
    )
    for row in worst:
        if row.get("user_message") in ml_by_message:
            add(row, "worst_ml_score")
        if len(candidates) >= args.limit:
            break

    if len(candidates) < args.limit:
        step = max(1, len(silver) // max(1, args.limit - len(candidates)))
        for idx, row in enumerate(silver):
            if idx % step == 0:
                add(row, "deterministic_sample")
            if len(candidates) >= args.limit:
                break

    save_jsonl(candidates[: args.limit], Path(args.output))
    print(f"rows: {len(candidates[: args.limit])}")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()
