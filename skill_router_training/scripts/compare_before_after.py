#!/usr/bin/env python3
"""Compare skill routing before and after enabling SkillRouter."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))


def load_jsonl(path: Optional[str]) -> List[Dict]:
    if not path:
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def normalize_skill_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    output = []
    seen = set()
    for item in value:
        if isinstance(item, dict):
            name = str(item.get("skill_name") or item.get("skill") or item.get("name") or "").strip()
        else:
            name = str(item or "").strip()
        if name and name not in seen:
            seen.add(name)
            output.append(name)
    return output


def row_key(row: Dict, index: int) -> str:
    for key in ("request_id", "query_sha256", "user_message"):
        value = str(row.get(key) or "").strip()
        if value:
            return f"{key}:{value}"
    return f"index:{index}"


def selected_skills(row: Dict) -> List[str]:
    for key in ("selected_skills", "selected_skill_names"):
        skills = normalize_skill_list(row.get(key))
        if skills:
            return skills
    return []


def baseline_from_after(row: Dict) -> List[str]:
    shadow = row.get("shadow_comparison")
    if isinstance(shadow, dict):
        skills = normalize_skill_list(shadow.get("baseline_skills"))
        if skills:
            return skills
    return []


def ideal_skills(row: Dict) -> List[str]:
    return normalize_skill_list(row.get("ideal_skills"))


def float_value(row: Dict, key: str) -> Optional[float]:
    try:
        value = row.get(key)
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(np.array(values, dtype=float), p))


def pair_rows(before_rows: List[Dict], after_rows: List[Dict]) -> List[Dict]:
    before_by_key = {row_key(row, idx): row for idx, row in enumerate(before_rows)}
    after_by_key = {row_key(row, idx): row for idx, row in enumerate(after_rows)}
    shared_keys = [key for key in after_by_key if key in before_by_key]

    pairs = []
    if shared_keys:
        for key in shared_keys:
            pairs.append(make_pair(key, before_by_key[key], after_by_key[key]))
        return pairs

    if before_rows:
        for idx, after in enumerate(after_rows):
            before = before_rows[idx] if idx < len(before_rows) else {}
            pairs.append(make_pair(f"index:{idx}", before, after))
        return pairs

    for idx, after in enumerate(after_rows):
        baseline = baseline_from_after(after)
        before = {"selected_skills": baseline} if baseline else {}
        pairs.append(make_pair(row_key(after, idx), before, after))
    return pairs


def make_pair(key: str, before: Dict, after: Dict) -> Dict:
    before_selected = selected_skills(before) or baseline_from_after(after)
    after_selected = selected_skills(after)
    ideal = ideal_skills(after) or ideal_skills(before)
    before_set = set(before_selected)
    after_set = set(after_selected)
    ideal_set = set(ideal)

    added = sorted(after_set - before_set)
    removed = sorted(before_set - after_set)
    retained = sorted(before_set & after_set)
    union = before_set | after_set
    jaccard = len(before_set & after_set) / len(union) if union else 1.0

    before_quality = quality_metrics(before_set, ideal_set)
    after_quality = quality_metrics(after_set, ideal_set)

    return {
        "key": key,
        "user_message": after.get("user_message") or before.get("user_message") or "",
        "before_selected": before_selected,
        "after_selected": after_selected,
        "ideal_skills": ideal,
        "before_count": len(before_selected),
        "after_count": len(after_selected),
        "delta_count": len(after_selected) - len(before_selected),
        "added": added,
        "removed": removed,
        "retained": retained,
        "jaccard": jaccard,
        "before_selection_score": float_value(before, "selection_score"),
        "after_selection_score": float_value(after, "selection_score"),
        "before_token_waste_ratio": float_value(before, "token_waste_ratio"),
        "after_token_waste_ratio": float_value(after, "token_waste_ratio"),
        "before_precision": before_quality["precision"],
        "before_recall": before_quality["recall"],
        "before_f1": before_quality["f1"],
        "after_precision": after_quality["precision"],
        "after_recall": after_quality["recall"],
        "after_f1": after_quality["f1"],
        "has_ideal": bool(ideal),
        "after_ok": after.get("ok"),
        "after_error": after.get("error"),
        "latency_ms": float_value(after, "latency_ms"),
        "plugin_latency_ms": float_value(after, "plugin_latency_ms"),
    }


def quality_metrics(selected: set, ideal: set) -> Dict[str, float]:
    if not ideal:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    tp = len(selected & ideal)
    precision = tp / len(selected) if selected else 0.0
    recall = tp / len(ideal) if ideal else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def summarize(pairs: List[Dict]) -> Dict:
    count = len(pairs)
    before_counts = [p["before_count"] for p in pairs]
    after_counts = [p["after_count"] for p in pairs]
    latencies = [p["latency_ms"] for p in pairs if p["latency_ms"] is not None]
    plugin_latencies = [p["plugin_latency_ms"] for p in pairs if p["plugin_latency_ms"] is not None]
    ideal_pairs = [p for p in pairs if p["has_ideal"]]

    before_avg = mean(before_counts) if before_counts else 0.0
    after_avg = mean(after_counts) if after_counts else 0.0
    reduction = (before_avg - after_avg) / before_avg if before_avg else 0.0

    return {
        "rows": count,
        "avg_before_selected": before_avg,
        "avg_after_selected": after_avg,
        "avg_delta_selected": (mean([p["delta_count"] for p in pairs]) if pairs else 0.0),
        "selected_count_reduction": reduction,
        "avg_jaccard": mean([p["jaccard"] for p in pairs]) if pairs else 0.0,
        "exact_same_rate": mean([1.0 if p["before_selected"] == p["after_selected"] else 0.0 for p in pairs])
        if pairs
        else 0.0,
        "avg_added_per_request": mean([len(p["added"]) for p in pairs]) if pairs else 0.0,
        "avg_removed_per_request": mean([len(p["removed"]) for p in pairs]) if pairs else 0.0,
        "quality_rows": len(ideal_pairs),
        "before_precision": mean([p["before_precision"] for p in ideal_pairs]) if ideal_pairs else None,
        "before_recall": mean([p["before_recall"] for p in ideal_pairs]) if ideal_pairs else None,
        "before_f1": mean([p["before_f1"] for p in ideal_pairs]) if ideal_pairs else None,
        "after_precision": mean([p["after_precision"] for p in ideal_pairs]) if ideal_pairs else None,
        "after_recall": mean([p["after_recall"] for p in ideal_pairs]) if ideal_pairs else None,
        "after_f1": mean([p["after_f1"] for p in ideal_pairs]) if ideal_pairs else None,
        "before_selection_score": mean([p["before_selection_score"] for p in pairs if p["before_selection_score"] is not None])
        if any(p["before_selection_score"] is not None for p in pairs)
        else None,
        "after_selection_score": mean([p["after_selection_score"] for p in pairs if p["after_selection_score"] is not None])
        if any(p["after_selection_score"] is not None for p in pairs)
        else None,
        "before_token_waste_ratio": mean([p["before_token_waste_ratio"] for p in pairs if p["before_token_waste_ratio"] is not None])
        if any(p["before_token_waste_ratio"] is not None for p in pairs)
        else None,
        "after_token_waste_ratio": mean([p["after_token_waste_ratio"] for p in pairs if p["after_token_waste_ratio"] is not None])
        if any(p["after_token_waste_ratio"] is not None for p in pairs)
        else None,
        "after_ok_rate": mean([1.0 if p["after_ok"] is True else 0.0 for p in pairs if p["after_ok"] is not None])
        if any(p["after_ok"] is not None for p in pairs)
        else None,
        "latency_p50_ms": percentile(latencies, 50),
        "latency_p95_ms": percentile(latencies, 95),
        "plugin_latency_p50_ms": percentile(plugin_latencies, 50),
        "plugin_latency_p95_ms": percentile(plugin_latencies, 95),
    }


def setup_plot_style() -> None:
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Liberation Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def pct(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def num(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def save_summary_chart(summary: Dict, output_path: Path) -> None:
    labels = ["Before", "After"]
    values = [summary["avg_before_selected"], summary["avg_after_selected"]]
    colors = ["#FF6B6B", "#4ECDC4"]
    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(labels, values, color=colors)
    ax.set_title("Average Selected Skill Count")
    ax.set_ylabel("Skills per Request")
    ax.set_ylim(0, max(values + [1]) * 1.25)
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{bar.get_height():.2f}", ha="center", va="bottom")
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_count_distribution(pairs: List[Dict], output_path: Path) -> None:
    before = [p["before_count"] for p in pairs]
    after = [p["after_count"] for p in pairs]
    max_count = max(before + after + [1])
    bins = np.arange(-0.5, max_count + 1.5, 1)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(before, bins=bins, alpha=0.65, label="Before", color="#FF6B6B", edgecolor="black")
    ax.hist(after, bins=bins, alpha=0.65, label="After", color="#4ECDC4", edgecolor="black")
    ax.set_title("Selected Skill Count Distribution")
    ax.set_xlabel("Selected Skill Count")
    ax.set_ylabel("Requests")
    ax.set_xticks(range(0, max_count + 1))
    ax.legend()
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_delta_distribution(pairs: List[Dict], output_path: Path) -> None:
    deltas = [p["delta_count"] for p in pairs]
    min_delta = min(deltas + [0])
    max_delta = max(deltas + [0])
    bins = np.arange(min_delta - 0.5, max_delta + 1.5, 1)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(deltas, bins=bins, color="#7C83FD", edgecolor="black", alpha=0.8)
    ax.axvline(0, color="#222222", linestyle="--", linewidth=1.5)
    ax.set_title("Change in Selected Skill Count")
    ax.set_xlabel("After Count - Before Count")
    ax.set_ylabel("Requests")
    ax.set_xticks(range(min_delta, max_delta + 1))
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_top_changes(pairs: List[Dict], output_path: Path, limit: int = 12) -> Tuple[Counter, Counter]:
    added = Counter()
    removed = Counter()
    for pair in pairs:
        added.update(pair["added"])
        removed.update(pair["removed"])

    top_added = added.most_common(limit)
    top_removed = removed.most_common(limit)
    labels = [f"+ {name}" for name, _ in top_added] + [f"- {name}" for name, _ in top_removed]
    values = [count for _, count in top_added] + [-count for _, count in top_removed]
    colors = ["#4ECDC4"] * len(top_added) + ["#FF6B6B"] * len(top_removed)

    fig, ax = plt.subplots(figsize=(10, max(5, 0.35 * max(1, len(labels)))))
    y = np.arange(len(labels))
    ax.barh(y, values, color=colors)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.axvline(0, color="#222222", linewidth=1)
    ax.set_title("Top Added and Removed Skills")
    ax.set_xlabel("Request Count")
    ax.invert_yaxis()
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return added, removed


def save_quality_chart(summary: Dict, output_path: Path) -> None:
    labels = []
    before = []
    after = []
    for key, title in (
        ("precision", "Precision"),
        ("recall", "Recall"),
        ("f1", "F1"),
    ):
        b = summary.get(f"before_{key}")
        a = summary.get(f"after_{key}")
        if b is not None and a is not None:
            labels.append(title)
            before.append(b * 100)
            after.append(a * 100)
    if not labels:
        return

    x = np.arange(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width / 2, before, width, label="Before", color="#FF6B6B")
    ax.bar(x + width / 2, after, width, label="After", color="#4ECDC4")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("%")
    ax.set_ylim(0, 100)
    ax.set_title("Quality Metrics on Labeled Rows")
    ax.legend()
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_score_waste_chart(summary: Dict, output_path: Path) -> None:
    labels = []
    before = []
    after = []
    for key, title in (
        ("selection_score", "Score"),
        ("token_waste_ratio", "Waste"),
    ):
        b = summary.get(f"before_{key}")
        a = summary.get(f"after_{key}")
        if b is not None and a is not None:
            labels.append(title)
            before.append(b * 100)
            after.append(a * 100)
    if not labels:
        return

    x = np.arange(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(x - width / 2, before, width, label="Before", color="#FF6B6B")
    ax.bar(x + width / 2, after, width, label="After", color="#4ECDC4")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("%")
    ax.set_ylim(0, 100)
    ax.set_title("Embedded Score and Waste Metrics")
    ax.legend()
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_latency_chart(summary: Dict, output_path: Path) -> None:
    values = []
    labels = []
    for key, title in (
        ("latency_p50_ms", "Router P50"),
        ("latency_p95_ms", "Router P95"),
        ("plugin_latency_p50_ms", "Plugin P50"),
        ("plugin_latency_p95_ms", "Plugin P95"),
    ):
        value = summary.get(key)
        if value:
            labels.append(title)
            values.append(value)
    if not labels:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, color="#FFC857")
    ax.set_title("Routing Latency")
    ax.set_ylabel("ms")
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{bar.get_height():.1f}", ha="center", va="bottom")
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def write_pairs_csv(pairs: List[Dict], path: Path) -> None:
    fieldnames = [
        "key",
        "before_count",
        "after_count",
        "delta_count",
        "jaccard",
        "before_selected",
        "after_selected",
        "added",
        "removed",
        "ideal_skills",
        "before_f1",
        "after_f1",
        "latency_ms",
        "plugin_latency_ms",
        "after_ok",
        "after_error",
    ]
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for pair in pairs:
            row = dict(pair)
            for key in ("before_selected", "after_selected", "added", "removed", "ideal_skills"):
                row[key] = ", ".join(row.get(key) or [])
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_summary_md(summary: Dict, added: Counter, removed: Counter, path: Path) -> None:
    lines = [
        "# SkillRouter Before/After Report",
        "",
        "## Summary",
        "",
        f"- Rows: `{summary['rows']}`",
        f"- Avg selected before: `{num(summary['avg_before_selected'])}`",
        f"- Avg selected after: `{num(summary['avg_after_selected'])}`",
        f"- Selected-count reduction: `{pct(summary['selected_count_reduction'])}`",
        f"- Avg Jaccard overlap: `{pct(summary['avg_jaccard'])}`",
        f"- Exact same route rate: `{pct(summary['exact_same_rate'])}`",
        f"- Avg added/request: `{num(summary['avg_added_per_request'])}`",
        f"- Avg removed/request: `{num(summary['avg_removed_per_request'])}`",
        "",
    ]

    if summary.get("quality_rows"):
        lines.extend(
            [
                "## Quality",
                "",
                f"- Labeled rows: `{summary['quality_rows']}`",
                f"- Before precision / recall / F1: `{pct(summary['before_precision'])}` / `{pct(summary['before_recall'])}` / `{pct(summary['before_f1'])}`",
                f"- After precision / recall / F1: `{pct(summary['after_precision'])}` / `{pct(summary['after_recall'])}` / `{pct(summary['after_f1'])}`",
                "",
            ]
        )

    if summary.get("before_selection_score") is not None:
        lines.extend(
            [
                "## Embedded Metrics",
                "",
                f"- Before score: `{pct(summary['before_selection_score'])}`",
                f"- After score: `{pct(summary['after_selection_score'])}`",
                f"- Before waste: `{pct(summary['before_token_waste_ratio'])}`",
                f"- After waste: `{pct(summary['after_token_waste_ratio'])}`",
                "",
            ]
        )

    if summary.get("after_ok_rate") is not None:
        lines.extend(["## Runtime", "", f"- After OK rate: `{pct(summary['after_ok_rate'])}`"])
        if summary.get("latency_p50_ms"):
            lines.append(
                f"- Router latency P50/P95: `{num(summary['latency_p50_ms'])} ms` / `{num(summary['latency_p95_ms'])} ms`"
            )
        if summary.get("plugin_latency_p50_ms"):
            lines.append(
                f"- Plugin latency P50/P95: `{num(summary['plugin_latency_p50_ms'])} ms` / `{num(summary['plugin_latency_p95_ms'])} ms`"
            )
        lines.append("")

    lines.extend(["## Top Added Skills", ""])
    if added:
        for skill, count in added.most_common(15):
            lines.append(f"- `{skill}`: {count}")
    else:
        lines.append("- None")
    lines.extend(["", "## Top Removed Skills", ""])
    if removed:
        for skill, count in removed.most_common(15):
            lines.append(f"- `{skill}`: {count}")
    else:
        lines.append("- None")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare routing before and after enabling SkillRouter.")
    parser.add_argument("--before", default="", help="Before/legacy routing JSONL. Optional if --after contains shadow baseline.")
    parser.add_argument("--after", required=True, help="After/SkillRouter JSONL or audit JSONL.")
    parser.add_argument("--output-dir", required=True, help="Output directory for charts and reports.")
    args = parser.parse_args()

    setup_plot_style()
    before_rows = load_jsonl(args.before)
    after_rows = load_jsonl(args.after)
    pairs = pair_rows(before_rows, after_rows)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize(pairs)

    save_summary_chart(summary, output_dir / "1_avg_selected_count.png")
    save_count_distribution(pairs, output_dir / "2_selected_count_distribution.png")
    save_delta_distribution(pairs, output_dir / "3_selected_count_delta.png")
    added, removed = save_top_changes(pairs, output_dir / "4_top_skill_changes.png")
    save_quality_chart(summary, output_dir / "5_quality_metrics.png")
    save_score_waste_chart(summary, output_dir / "6_score_waste.png")
    save_latency_chart(summary, output_dir / "7_latency.png")
    write_pairs_csv(pairs, output_dir / "paired_rows.csv")
    write_summary_md(summary, added, removed, output_dir / "summary.md")

    print(f"Rows: {summary['rows']}")
    print(f"Avg selected: before={summary['avg_before_selected']:.2f}, after={summary['avg_after_selected']:.2f}")
    print(f"Selected-count reduction: {summary['selected_count_reduction'] * 100:.1f}%")
    print(f"Report: {output_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
