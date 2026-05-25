#!/usr/bin/env python3
"""
Compare multiple SkillRouter output JSONL files against their embedded labels.

Each input row is expected to contain:
- user_message
- ideal_skills
- selected_skills
- selection_score
- token_waste_ratio
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

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


def parse_run(value: str) -> Tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.stem, path
    name, path = value.split("=", 1)
    return name.strip(), Path(path.strip())


def skill_sets(row: Dict) -> Tuple[set, set]:
    selected = set(row.get("selected_skills") or [])
    ideal = set(row.get("ideal_skills") or [])
    return selected, ideal


def compute_metrics(rows: List[Dict]) -> Dict:
    n = len(rows)
    if n == 0:
        return {
            "rows": 0,
            "selection_score": 0.0,
            "token_waste_ratio": 0.0,
            "exact_match": 0.0,
            "avg_selected": 0.0,
            "avg_ideal": 0.0,
            "micro_precision": 0.0,
            "micro_recall": 0.0,
            "micro_f1": 0.0,
            "avg_extra_skills": 0.0,
            "avg_missing_skills": 0.0,
        }

    total_score = sum(float(row.get("selection_score", 0.0)) for row in rows)
    total_waste = sum(float(row.get("token_waste_ratio", 0.0)) for row in rows)
    exact = 0
    total_selected = 0
    total_ideal = 0
    true_positive = 0
    total_extra = 0
    total_missing = 0

    for row in rows:
        selected, ideal = skill_sets(row)
        exact += selected == ideal
        total_selected += len(selected)
        total_ideal += len(ideal)
        true_positive += len(selected & ideal)
        total_extra += len(selected - ideal)
        total_missing += len(ideal - selected)

    precision = true_positive / total_selected if total_selected else 0.0
    recall = true_positive / total_ideal if total_ideal else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "rows": n,
        "selection_score": total_score / n,
        "token_waste_ratio": total_waste / n,
        "exact_match": exact / n,
        "avg_selected": total_selected / n,
        "avg_ideal": total_ideal / n,
        "micro_precision": precision,
        "micro_recall": recall,
        "micro_f1": f1,
        "avg_extra_skills": total_extra / n,
        "avg_missing_skills": total_missing / n,
    }


def collect_error_counters(rows: Iterable[Dict]) -> Tuple[Counter, Counter]:
    extra = Counter()
    missing = Counter()
    for row in rows:
        selected, ideal = skill_sets(row)
        extra.update(selected - ideal)
        missing.update(ideal - selected)
    return extra, missing


def worst_rows(rows: List[Dict], limit: int) -> List[Dict]:
    indexed = []
    for idx, row in enumerate(rows, start=1):
        selected, ideal = skill_sets(row)
        indexed.append(
            {
                "row": idx,
                "selection_score": float(row.get("selection_score", 0.0)),
                "token_waste_ratio": float(row.get("token_waste_ratio", 0.0)),
                "selected_skills": sorted(selected),
                "ideal_skills": sorted(ideal),
                "extra_skills": sorted(selected - ideal),
                "missing_skills": sorted(ideal - selected),
                "user_message": (row.get("user_message") or "").replace("\n", " ")[:180],
            }
        )
    indexed.sort(
        key=lambda item: (
            item["selection_score"],
            -len(item["missing_skills"]),
            -len(item["extra_skills"]),
            -item["token_waste_ratio"],
        )
    )
    return indexed[:limit]


def format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def write_csv(summary: List[Dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "name",
        "rows",
        "selection_score",
        "token_waste_ratio",
        "exact_match",
        "avg_selected",
        "avg_ideal",
        "micro_precision",
        "micro_recall",
        "micro_f1",
        "avg_extra_skills",
        "avg_missing_skills",
    ]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_markdown(report: Dict[str, Dict], path: Path, worst_limit: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Skill Router Evaluation Report",
        "",
        "## Summary",
        "",
        "| Run | Rows | Score | Waste | Exact | Avg selected | Avg ideal | Precision | Recall | Micro F1 | Extra/request | Missing/request |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for name, item in report.items():
        m = item["metrics"]
        lines.append(
            "| {name} | {rows} | {score} | {waste} | {exact} | {avg_selected:.2f} | "
            "{avg_ideal:.2f} | {precision} | {recall} | {f1} | {extra:.2f} | {missing:.2f} |".format(
                name=name,
                rows=m["rows"],
                score=format_pct(m["selection_score"]),
                waste=format_pct(m["token_waste_ratio"]),
                exact=format_pct(m["exact_match"]),
                avg_selected=m["avg_selected"],
                avg_ideal=m["avg_ideal"],
                precision=format_pct(m["micro_precision"]),
                recall=format_pct(m["micro_recall"]),
                f1=format_pct(m["micro_f1"]),
                extra=m["avg_extra_skills"],
                missing=m["avg_missing_skills"],
            )
        )

    for name, item in report.items():
        extra = item["extra"]
        missing = item["missing"]
        lines.extend(
            [
                "",
                f"## {name}",
                "",
                "### Top Extra Skills",
                "",
            ]
        )
        if extra:
            for skill, count in extra.most_common(10):
                lines.append(f"- `{skill}`: {count}")
        else:
            lines.append("- None")

        lines.extend(["", "### Top Missing Skills", ""])
        if missing:
            for skill, count in missing.most_common(10):
                lines.append(f"- `{skill}`: {count}")
        else:
            lines.append("- None")

        lines.extend(["", f"### Worst {worst_limit} Rows", ""])
        for row in item["worst"]:
            lines.append(
                "- row {row}, score={score:.3f}, waste={waste:.3f}, missing={missing}, extra={extra}: {msg}".format(
                    row=row["row"],
                    score=row["selection_score"],
                    waste=row["token_waste_ratio"],
                    missing=", ".join(row["missing_skills"]) or "None",
                    extra=", ".join(row["extra_skills"]) or "None",
                    msg=row["user_message"],
                )
            )

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Compare SkillRouter result JSONL files.")
    parser.add_argument(
        "--run",
        action="append",
        required=True,
        help="Run definition as name=path. Can be repeated.",
    )
    parser.add_argument(
        "--output-md",
        default=str(PACKAGE_ROOT / "data" / "router_comparison_report.md"),
    )
    parser.add_argument(
        "--output-csv",
        default=str(PACKAGE_ROOT / "data" / "router_comparison_summary.csv"),
    )
    parser.add_argument("--worst-limit", type=int, default=10)
    args = parser.parse_args()

    report = {}
    summary = []

    for run in args.run:
        name, path = parse_run(run)
        rows = load_jsonl(path)
        metrics = compute_metrics(rows)
        extra, missing = collect_error_counters(rows)
        report[name] = {
            "path": str(path),
            "metrics": metrics,
            "extra": extra,
            "missing": missing,
            "worst": worst_rows(rows, args.worst_limit),
        }
        summary.append({"name": name, **metrics})

    write_csv(summary, Path(args.output_csv))
    write_markdown(report, Path(args.output_md), args.worst_limit)

    print("Summary")
    for row in summary:
        print(
            "{name}: score={score:.3f}, waste={waste:.3f}, precision={precision:.3f}, "
            "recall={recall:.3f}, f1={f1:.3f}, selected={selected:.2f}, ideal={ideal:.2f}".format(
                name=row["name"],
                score=row["selection_score"],
                waste=row["token_waste_ratio"],
                precision=row["micro_precision"],
                recall=row["micro_recall"],
                f1=row["micro_f1"],
                selected=row["avg_selected"],
                ideal=row["avg_ideal"],
            )
        )
    print(f"markdown: {args.output_md}")
    print(f"csv: {args.output_csv}")


if __name__ == "__main__":
    main()
