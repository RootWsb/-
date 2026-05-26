#!/usr/bin/env python3
"""Merge real prod labels with synthetic router training rows."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List


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


def normalize_real_rows(rows: List[Dict[str, Any]], weight: float) -> List[Dict[str, Any]]:
    output = []
    for row in rows:
        item = dict(row)
        item.setdefault("data_source", "real_prod")
        item["sample_weight"] = weight
        output.append(item)
    return output


def filter_synthetic_rows(
    rows: List[Dict[str, Any]],
    min_weight: float,
    synthetic_weight: float | None = None,
) -> List[Dict[str, Any]]:
    output = []
    for row in rows:
        weight = float(row.get("sample_weight") or 0.0)
        if weight < min_weight:
            continue
        if not row.get("ideal_skills"):
            continue
        item = dict(row)
        if synthetic_weight is not None:
            item["sample_weight"] = synthetic_weight
        output.append(item)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build mixed real+synthetic SkillRouter training data.")
    parser.add_argument("--real", default="data_prod/training_data.jsonl")
    parser.add_argument("--synthetic", default="data_prod/synthetic_training_data_1000.jsonl")
    parser.add_argument("--output", default="data_prod/training_data_mixed_1000.jsonl")
    parser.add_argument("--real-weight", type=float, default=1.0)
    parser.add_argument("--min-synthetic-weight", type=float, default=0.1)
    parser.add_argument(
        "--synthetic-weight",
        type=float,
        default=None,
        help="Override sample_weight for all kept synthetic rows.",
    )
    args = parser.parse_args()

    real_rows = normalize_real_rows(load_jsonl(Path(args.real)), args.real_weight)
    synthetic_rows = filter_synthetic_rows(
        load_jsonl(Path(args.synthetic)),
        args.min_synthetic_weight,
        args.synthetic_weight,
    )
    merged = real_rows + synthetic_rows
    save_jsonl(merged, Path(args.output))

    sources = Counter(row.get("data_source", "unknown") for row in merged)
    confidence = Counter(row.get("confidence", "") for row in synthetic_rows)
    print(f"real_rows: {len(real_rows)}")
    print(f"synthetic_rows: {len(synthetic_rows)}")
    print(f"merged_rows: {len(merged)}")
    print(f"sources: {dict(sources)}")
    print(f"synthetic_confidence: {dict(confidence)}")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()
