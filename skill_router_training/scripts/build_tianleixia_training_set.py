#!/usr/bin/env python3
"""
Build Tianleixia-focused SkillRouter training sets.

This script starts from the existing training_data.jsonl and appends confirmed
gold labels from Tianleixia logs. It can also create a first-layer version that
removes internal/runtime skills from labels.
"""

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Set

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


def save_jsonl(rows: Iterable[Dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_skill_index(path: Path) -> Dict[str, int]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_excluded_skills(policy_path: Path) -> Set[str]:
    if not policy_path.exists():
        return set()
    with open(policy_path, "r", encoding="utf-8") as f:
        policy = json.load(f)
    return set(policy.get("excluded_skills") or [])


def normalize_labels(skills: Iterable[str], skill_index: Dict[str, int], excluded: Set[str]) -> List[str]:
    labels = []
    seen = set()
    for skill in skills or []:
        if skill in excluded:
            continue
        if skill not in skill_index:
            continue
        if skill not in seen:
            seen.add(skill)
            labels.append(skill)
    return sorted(labels, key=lambda name: skill_index[name])


def make_skill_labels(skills: Iterable[str], skill_index: Dict[str, int]) -> List[int]:
    labels = [0] * len(skill_index)
    for skill in skills:
        if skill in skill_index:
            labels[skill_index[skill]] = 1
    return labels


def normalize_training_row(row: Dict, skill_index: Dict[str, int], excluded: Set[str]) -> Dict:
    ideal = normalize_labels(row.get("ideal_skills") or [], skill_index, excluded)
    return {
        **row,
        "ideal_skills": ideal,
        "skill_labels": make_skill_labels(ideal, skill_index),
    }


def gold_row_to_training(row: Dict, skill_index: Dict[str, int], excluded: Set[str]) -> Dict:
    raw_ideal = row.get("gold_ideal_skills") or row.get("ideal_skills") or []
    ideal = normalize_labels(raw_ideal, skill_index, excluded)
    return {
        "user_message": row.get("user_message", ""),
        "ideal_skills": ideal,
        "skill_labels": make_skill_labels(ideal, skill_index),
        "score": 1.0,
        "token_efficiency": 0.0,
        "data_source": "tianleixia_gold",
        "source": row.get("source", "tianleixia_gold_review"),
        "workspace_name": row.get("workspace_name", ""),
        "label_confidence": "gold",
    }


def gold_row_to_eval(row: Dict, skill_index: Dict[str, int], excluded: Set[str]) -> Dict:
    raw_ideal = row.get("gold_ideal_skills") or row.get("ideal_skills") or []
    ideal = normalize_labels(raw_ideal, skill_index, excluded)
    return {
        "user_message": row.get("user_message", ""),
        "ideal_skills": ideal,
        "source": "tianleixia_gold_holdout",
        "workspace_name": row.get("workspace_name", ""),
        "label_confidence": "gold",
        "gold_notes": row.get("gold_notes", ""),
    }


def summarize(rows: List[Dict], name: str):
    source_counter = Counter(row.get("data_source", "unknown") for row in rows)
    skill_counter = Counter()
    for row in rows:
        skill_counter.update(row.get("ideal_skills") or [])
    zero_count = sum(1 for row in rows if not row.get("ideal_skills"))

    print(f"\n{name}")
    print(f"  rows: {len(rows)}")
    print(f"  zero-skill rows: {zero_count}")
    print("  sources:")
    for source, count in source_counter.most_common():
        print(f"    {source}: {count}")
    print("  top skills:")
    for skill, count in skill_counter.most_common(12):
        print(f"    {skill}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Build Tianleixia training data.")
    parser.add_argument(
        "--base-training",
        default=str(PACKAGE_ROOT / "data" / "training_data.jsonl"),
    )
    parser.add_argument(
        "--gold",
        default=str(PACKAGE_ROOT / "data" / "tianleixia_gold_review_50.jsonl"),
    )
    parser.add_argument(
        "--skill-index",
        default=str(PACKAGE_ROOT / "data" / "skill_index.json"),
    )
    parser.add_argument(
        "--policy",
        default=str(PACKAGE_ROOT / "data" / "first_layer_routing_policy.json"),
    )
    parser.add_argument(
        "--output-full",
        default=str(PACKAGE_ROOT / "data" / "training_data_tianleixia_gold.jsonl"),
    )
    parser.add_argument(
        "--output-first-layer",
        default=str(PACKAGE_ROOT / "data" / "training_data_tianleixia_first_layer.jsonl"),
    )
    parser.add_argument(
        "--output-holdout",
        default=str(PACKAGE_ROOT / "data" / "tianleixia_gold_holdout.jsonl"),
    )
    parser.add_argument(
        "--gold-repeat",
        type=int,
        default=8,
        help="Repeat gold rows to make the small confirmed set visible during training.",
    )
    parser.add_argument(
        "--gold-holdout-ratio",
        type=float,
        default=0.2,
        help="Gold ratio kept out of training for honest evaluation.",
    )
    parser.add_argument("--gold-split-seed", type=int, default=42)
    parser.add_argument(
        "--use-all-gold",
        action="store_true",
        help="Use all gold rows for training. Do this only after creating a separate test set.",
    )
    args = parser.parse_args()

    skill_index = load_skill_index(Path(args.skill_index))
    excluded = load_excluded_skills(Path(args.policy))
    base_rows = load_jsonl(Path(args.base_training))
    gold_rows = load_jsonl(Path(args.gold))

    shuffled_gold = list(gold_rows)
    random.Random(args.gold_split_seed).shuffle(shuffled_gold)
    if args.use_all_gold:
        train_gold_rows = shuffled_gold
        holdout_gold_rows = []
    else:
        holdout_count = max(1, round(len(shuffled_gold) * args.gold_holdout_ratio)) if shuffled_gold else 0
        holdout_gold_rows = shuffled_gold[:holdout_count]
        train_gold_rows = shuffled_gold[holdout_count:]

    normalized_base = [normalize_training_row(row, skill_index, excluded=set()) for row in base_rows]
    full_gold = [gold_row_to_training(row, skill_index, excluded=set()) for row in train_gold_rows]
    full_rows = normalized_base + full_gold * max(1, args.gold_repeat)

    first_layer_base = [normalize_training_row(row, skill_index, excluded=excluded) for row in base_rows]
    first_layer_gold = [gold_row_to_training(row, skill_index, excluded=excluded) for row in train_gold_rows]
    first_layer_rows = first_layer_base + first_layer_gold * max(1, args.gold_repeat)
    holdout_rows = [gold_row_to_eval(row, skill_index, excluded=set()) for row in holdout_gold_rows]

    save_jsonl(full_rows, Path(args.output_full))
    save_jsonl(first_layer_rows, Path(args.output_first_layer))
    save_jsonl(holdout_rows, Path(args.output_holdout))

    print(f"gold train rows: {len(train_gold_rows)}")
    print(f"gold holdout rows: {len(holdout_rows)}")
    summarize(full_rows, "Full training set")
    summarize(first_layer_rows, "First-layer training set")
    print(f"\noutput_full: {args.output_full}")
    print(f"output_first_layer: {args.output_first_layer}")
    print(f"output_holdout: {args.output_holdout}")


if __name__ == "__main__":
    main()
