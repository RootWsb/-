#!/usr/bin/env python3
"""Generate a release or rollback recommendation from router evaluation outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def skill_sets(row: Dict[str, Any]) -> Tuple[set[str], set[str]]:
    return set(row.get("selected_skills") or []), set(row.get("ideal_skills") or [])


def metrics(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    n = len(rows)
    if not rows:
        return {
            "rows": 0,
            "selection_score": 0.0,
            "token_waste_ratio": 0.0,
            "micro_precision": 0.0,
            "micro_recall": 0.0,
            "micro_f1": 0.0,
            "avg_selected": 0.0,
            "avg_ideal": 0.0,
            "avg_extra_skills": 0.0,
            "avg_missing_skills": 0.0,
        }

    selected_total = ideal_total = tp_total = extra_total = missing_total = 0
    score_total = waste_total = 0.0
    for row in rows:
        selected, ideal = skill_sets(row)
        selected_total += len(selected)
        ideal_total += len(ideal)
        tp_total += len(selected & ideal)
        extra_total += len(selected - ideal)
        missing_total += len(ideal - selected)
        score_total += float(row.get("selection_score", 0.0))
        waste_total += float(row.get("token_waste_ratio", 0.0))

    precision = tp_total / selected_total if selected_total else 0.0
    recall = tp_total / ideal_total if ideal_total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "rows": float(n),
        "selection_score": score_total / n,
        "token_waste_ratio": waste_total / n,
        "micro_precision": precision,
        "micro_recall": recall,
        "micro_f1": f1,
        "avg_selected": selected_total / n,
        "avg_ideal": ideal_total / n,
        "avg_extra_skills": extra_total / n,
        "avg_missing_skills": missing_total / n,
    }


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def decide(current: Dict[str, float], candidate: Dict[str, float], args: argparse.Namespace) -> tuple[str, List[str]]:
    reasons = []
    f1_delta = candidate["micro_f1"] - current["micro_f1"]
    waste_delta = candidate["token_waste_ratio"] - current["token_waste_ratio"]
    missing_delta = candidate["avg_missing_skills"] - current["avg_missing_skills"]
    selected_limit = current["avg_selected"] * args.max_selected_ratio

    if candidate["rows"] < args.min_rows:
        reasons.append(f"评估样本不足：candidate rows={int(candidate['rows'])}, min_rows={args.min_rows}")

    blockers = []
    if f1_delta < 0:
        blockers.append(f"Micro F1 下降 {pct(abs(f1_delta))}")
    if waste_delta > args.max_waste_delta:
        blockers.append(f"token waste 上升 {pct(waste_delta)}，超过阈值 {pct(args.max_waste_delta)}")
    if missing_delta > args.max_missing_delta:
        blockers.append(f"missing/request 上升 {missing_delta:.2f}，超过阈值 {args.max_missing_delta:.2f}")
    if candidate["avg_selected"] > selected_limit:
        blockers.append(
            f"avg_selected={candidate['avg_selected']:.2f} 超过 current 的 {args.max_selected_ratio:.2f} 倍"
        )

    if blockers:
        return "BLOCK_RELEASE_OR_ROLL_BACK", reasons + blockers

    if (
        f1_delta >= args.min_f1_delta
        and waste_delta <= args.max_waste_delta
        and missing_delta <= args.max_missing_delta
        and candidate["avg_selected"] <= selected_limit
    ):
        return "ALLOW_SHADOW_OR_CANARY", reasons + [f"Micro F1 提升 {pct(f1_delta)}，且 waste/missing/selected 均在阈值内"]

    return "MANUAL_REVIEW", reasons + ["指标未触发阻断，但提升不足以自动放行"]


def write_markdown(
    path: Path,
    decision: str,
    reasons: List[str],
    current_name: str,
    candidate_name: str,
    current: Dict[str, float],
    candidate: Dict[str, float],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Router Release Decision",
        "",
        f"Decision: `{decision}`",
        "",
        "## Metrics",
        "",
        "| Run | Rows | Score | Waste | Precision | Recall | Micro F1 | Avg selected | Avg ideal | Extra/request | Missing/request |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, item in ((current_name, current), (candidate_name, candidate)):
        lines.append(
            "| {name} | {rows} | {score} | {waste} | {precision} | {recall} | {f1} | {selected:.2f} | {ideal:.2f} | {extra:.2f} | {missing:.2f} |".format(
                name=name,
                rows=int(item["rows"]),
                score=pct(item["selection_score"]),
                waste=pct(item["token_waste_ratio"]),
                precision=pct(item["micro_precision"]),
                recall=pct(item["micro_recall"]),
                f1=pct(item["micro_f1"]),
                selected=item["avg_selected"],
                ideal=item["avg_ideal"],
                extra=item["avg_extra_skills"],
                missing=item["avg_missing_skills"],
            )
        )

    lines.extend(["", "## Reasons", ""])
    lines.extend(f"- {reason}" for reason in reasons)
    lines.extend(
        [
            "",
            "## Operational Guidance",
            "",
            "- `ALLOW_SHADOW_OR_CANARY`: 只建议进入 shadow 或小流量灰度，仍需观察 failure rate、用户修正率和 P95 延迟。",
            "- `MANUAL_REVIEW`: 需要人工查看 worst rows 和核心 skill 漏选情况。",
            "- `BLOCK_RELEASE_OR_ROLL_BACK`: 不建议上线；如果该 candidate 已灰度，应回滚到 current checkpoint。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Make a router release/rollback decision.")
    parser.add_argument("--current", required=True, help="Current production evaluation JSONL.")
    parser.add_argument("--candidate", required=True, help="Candidate evaluation JSONL.")
    parser.add_argument("--current-name", default="CurrentML")
    parser.add_argument("--candidate-name", default="Candidate")
    parser.add_argument("--output-md", default="skill_router_training/data_prod/router_release_decision.md")
    parser.add_argument("--min-f1-delta", type=float, default=0.02)
    parser.add_argument("--max-waste-delta", type=float, default=0.03)
    parser.add_argument("--max-missing-delta", type=float, default=0.0)
    parser.add_argument("--max-selected-ratio", type=float, default=1.15)
    parser.add_argument("--min-rows", type=int, default=50)
    args = parser.parse_args()

    current = metrics(load_jsonl(Path(args.current)))
    candidate = metrics(load_jsonl(Path(args.candidate)))
    decision, reasons = decide(current, candidate, args)
    write_markdown(
        Path(args.output_md),
        decision,
        reasons,
        args.current_name,
        args.candidate_name,
        current,
        candidate,
    )

    print(f"decision: {decision}")
    for reason in reasons:
        print(f"- {reason}")
    print(f"output_md: {args.output_md}")


if __name__ == "__main__":
    main()
