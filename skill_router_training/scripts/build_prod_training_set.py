#!/usr/bin/env python3
"""
Build a production-skill training set from Tianleixia labels.

This is intentionally conservative:
- Converts existing old/abstract labels to real prod skill names.
- Adds keyword hints for NocoBase/OA sub-skills.
- Emits review files so the mapping can be checked before retraining.
"""

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))


OLD_TO_PROD = {
    "requirements-clarifier": [],
    "materials-to-problems": [],
    "wanxiangoa-api": ["oa-wanxiang-api-reader"],
    "writing-plans": ["writing-plans"],
    "test-driven-development": ["test-driven-development"],
    "systematic-debugging": ["systematic-debugging"],
    "dispatching-parallel-agents": ["dispatching-parallel-agents"],
    "using-git-worktrees": ["using-git-worktrees"],
    "using-superpowers": ["using-superpowers", "using-skills"],
    "writing-skills": ["writing-skills"],
    "executing-plans": ["executing-plans"],
    "subagent-driven-development": ["subagent-driven-development"],
    "nocobase-dev-setup": ["nocobase-env-manage", "nocobase-plugin-manage"],
    "execute-test-cases": [],
    "requirements-to-test-cases": [],
    "test-cases-to-execution-json": [],
    "playwright-cli": [],
    "send-file": [],
}


KEYWORD_RULES: Sequence[Tuple[str, Sequence[str], str]] = [
    ("brainstorming", ("需求", "设计", "方案", "规划", "还没想好", "怎么实现", "优化", "分析", "差异"), "clarification/design keyword"),
    ("nocobase-data-analysis", ("分析", "差异", "对比", "统计", "汇总", "报表", "分布"), "analysis keyword"),
    ("oa-wanxiang-modeling-api", ("数据表", "字段", "分类表", "树表", "表名", "主数据源", "建模"), "data-modeling keyword"),
    ("nocobase-data-modeling", ("数据表", "字段", "分类表", "树表", "表名", "主数据源", "建模"), "nocobase data-modeling keyword"),
    ("oa-wanxiang-page-api", ("页面", "区块", "表格区块", "视图", "菜单", "按钮", "弹窗"), "page/ui keyword"),
    ("nocobase-ui-builder", ("页面", "区块", "表格区块", "视图", "菜单", "按钮", "弹窗"), "nocobase ui keyword"),
    ("oa-wanxiang-workflow-api", ("工作流", "审批", "节点", "触发", "自动生成", "工单"), "workflow keyword"),
    ("nocobase-workflow-manage", ("工作流", "审批", "节点", "触发", "自动生成", "工单"), "nocobase workflow keyword"),
    ("oa-wanxiang-plugin-api", ("插件", "plugin", "import-pro", "导入pro", "history", "历史记录", "Oracle", "MSSQL", "SQL Server", "Kingbase", "外部数据源"), "plugin keyword"),
    ("nocobase-plugin-development", ("插件", "plugin", "import-pro", "导入pro", "history", "历史记录", "Oracle", "MSSQL", "SQL Server", "Kingbase", "外部数据源"), "nocobase plugin keyword"),
    ("nocobase-acl-manage", ("权限", "角色", "ACL", "访问控制"), "acl keyword"),
    ("systematic-debugging", ("报错", "错误", "失败", "不显示", "不能", "无法", "检查", "自检", "为什么"), "debug keyword"),
    ("test-driven-development", ("测试", "用例", "验证", "自检", "是否支持"), "test keyword"),
    ("writing-plans", ("计划", "方案", "实现", "开发", "优化", "补充功能", "拉取分支"), "planning keyword"),
]


PROD_INTERNAL_FIRST_LAYER_EXCLUDE = {
    "agent-system-control-panel",
    "agent-task-manage",
    "agent-task-orchestration",
    "using-skills",
    "using-superpowers",
    "executing-plans",
    "receiving-code-review",
    "requesting-code-review",
    "finishing-a-development-branch",
    "verification-before-completion",
}


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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


def save_review_markdown(rows: List[Dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Prod Skill Review Set",
        "",
        "Review the candidate prod labels, then edit `ideal_skills` in the JSONL file.",
        "",
    ]
    for idx, row in enumerate(rows, start=1):
        lines.extend(
            [
                f"## {idx}. {row.get('workspace_name') or 'unknown'}",
                "",
                f"- label_confidence: `{row.get('label_confidence', '')}`",
                f"- old_ideal_skills: `{', '.join(row.get('old_ideal_skills') or [])}`",
                f"- prod_candidate_skills: `{', '.join(row.get('ideal_skills') or [])}`",
                f"- mapping_reasons: `{'; '.join(row.get('mapping_reasons') or [])}`",
                "",
                "```text",
                row.get("user_message", ""),
                "```",
                "",
            ]
        )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def make_skill_labels(skills: Iterable[str], skill_index: Dict[str, int]) -> List[int]:
    labels = [0] * len(skill_index)
    for skill in skills:
        if skill in skill_index:
            labels[skill_index[skill]] = 1
    return labels


def add_label(labels: List[str], skill: str, skill_index: Dict[str, int], excluded: Set[str]):
    if skill in skill_index and skill not in excluded and skill not in labels:
        labels.append(skill)


def get_old_labels(row: Dict) -> List[str]:
    return list(row.get("gold_ideal_skills") or row.get("ideal_skills") or [])


def keyword_hits(text: str, keywords: Sequence[str]) -> bool:
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in keywords)


def map_to_prod(row: Dict, skill_index: Dict[str, int], excluded: Set[str]) -> Tuple[List[str], List[str]]:
    text = row.get("user_message") or ""
    old_labels = get_old_labels(row)
    labels: List[str] = []
    reasons: List[str] = []

    for old in old_labels:
        mapped = OLD_TO_PROD.get(old, [])
        if mapped:
            reasons.append(f"{old}->{','.join(mapped)}")
        for skill in mapped:
            add_label(labels, skill, skill_index, excluded)

    has_oa_context = any(
        token.lower() in text.lower()
        for token in (
            "万象",
            "oa",
            "nocobase",
            "插件",
            "页面",
            "区块",
            "数据表",
            "字段",
            "工作流",
            "审批",
            "导入",
            "oracle",
            "mssql",
            "kingbase",
            "sql server",
        )
    ) or "wanxiangoa-api" in old_labels

    if has_oa_context:
        add_label(labels, "oa-wanxiang-api-reader", skill_index, excluded)
        reasons.append("oa-context->oa-wanxiang-api-reader")

    for skill, keywords, reason in KEYWORD_RULES:
        if keyword_hits(text, keywords):
            add_label(labels, skill, skill_index, excluded)
            reasons.append(reason)

    labels.sort(key=lambda name: skill_index[name])
    return labels, reasons


def convert_row(row: Dict, skill_index: Dict[str, int], excluded: Set[str], source: str) -> Dict:
    labels, reasons = map_to_prod(row, skill_index, excluded)
    return {
        "user_message": row.get("user_message", ""),
        "ideal_skills": labels,
        "skill_labels": make_skill_labels(labels, skill_index),
        "score": 1.0 if row.get("label_confidence") == "gold" or row.get("gold_ideal_skills") else 0.8,
        "token_efficiency": 0.0,
        "data_source": source,
        "source": row.get("source", source),
        "workspace_name": row.get("workspace_name", ""),
        "label_confidence": row.get("label_confidence", "mapped"),
        "old_ideal_skills": get_old_labels(row),
        "mapping_reasons": reasons,
        "needs_review": row.get("label_confidence") != "high" or not labels or len(labels) >= 7,
    }


def summarize(rows: List[Dict], name: str):
    skill_counter = Counter()
    source_counter = Counter()
    review_count = 0
    for row in rows:
        skill_counter.update(row.get("ideal_skills") or [])
        source_counter[row.get("data_source", "unknown")] += 1
        review_count += bool(row.get("needs_review"))
    print(f"\n{name}")
    print(f"  rows: {len(rows)}")
    print(f"  zero-skill rows: {sum(1 for row in rows if not row.get('ideal_skills'))}")
    print(f"  needs_review rows: {review_count}")
    print("  sources:")
    for source, count in source_counter.most_common():
        print(f"    {source}: {count}")
    print("  top skills:")
    for skill, count in skill_counter.most_common(16):
        print(f"    {skill}: {count}")


def select_review_rows(rows: List[Dict], limit: int, seed: int) -> List[Dict]:
    scored = []
    for idx, row in enumerate(rows):
        score = 0
        if row.get("needs_review"):
            score += 10
        if row.get("label_confidence") == "gold":
            score += 6
        score += min(8, len(row.get("ideal_skills") or []))
        score += min(4, len(row.get("user_message", "")) // 300)
        scored.append((score, idx, row))
    rng = random.Random(seed)
    rng.shuffle(scored)
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [row for _, _, row in scored[:limit]]


def main():
    parser = argparse.ArgumentParser(description="Build prod-skill training data from Tianleixia logs.")
    parser.add_argument("--gold", default=str(PACKAGE_ROOT / "data" / "tianleixia_gold_review_50.jsonl"))
    parser.add_argument("--silver", default=str(PACKAGE_ROOT / "data" / "tianleixia_log_silver.jsonl"))
    parser.add_argument("--skill-index", default=str(PACKAGE_ROOT / "data" / "prod_skill_index.json"))
    parser.add_argument("--output-train", default=str(PACKAGE_ROOT / "data" / "prod_training_data_mapped.jsonl"))
    parser.add_argument("--output-review", default=str(PACKAGE_ROOT / "data" / "prod_gold_review_50.jsonl"))
    parser.add_argument("--output-review-md", default=str(PACKAGE_ROOT / "data" / "prod_gold_review_50.md"))
    parser.add_argument("--output-holdout", default=str(PACKAGE_ROOT / "data" / "prod_gold_holdout.jsonl"))
    parser.add_argument("--review-limit", type=int, default=50)
    parser.add_argument("--holdout-ratio", type=float, default=0.2)
    parser.add_argument("--gold-repeat", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-internal-first-layer", action="store_true")
    args = parser.parse_args()

    skill_index = load_json(Path(args.skill_index))
    excluded = set() if args.include_internal_first_layer else PROD_INTERNAL_FIRST_LAYER_EXCLUDE

    gold_rows = load_jsonl(Path(args.gold))
    silver_rows = load_jsonl(Path(args.silver))

    converted_gold = [convert_row(row, skill_index, excluded, "prod_mapped_gold") for row in gold_rows]
    converted_silver = [convert_row(row, skill_index, excluded, "prod_mapped_silver") for row in silver_rows]

    shuffled_gold = list(converted_gold)
    random.Random(args.seed).shuffle(shuffled_gold)
    holdout_count = max(1, round(len(shuffled_gold) * args.holdout_ratio)) if shuffled_gold else 0
    holdout_rows = shuffled_gold[:holdout_count]
    train_gold = shuffled_gold[holdout_count:]

    train_rows = converted_silver + train_gold * max(1, args.gold_repeat)
    review_rows = select_review_rows(converted_gold + converted_silver, args.review_limit, args.seed)

    save_jsonl(train_rows, Path(args.output_train))
    save_jsonl(review_rows, Path(args.output_review))
    save_review_markdown(review_rows, Path(args.output_review_md))
    save_jsonl(holdout_rows, Path(args.output_holdout))

    summarize(train_rows, "prod training data")
    summarize(review_rows, "prod review set")
    summarize(holdout_rows, "prod holdout")
    print(f"\noutput_train: {args.output_train}")
    print(f"output_review: {args.output_review}")
    print(f"output_review_md: {args.output_review_md}")
    print(f"output_holdout: {args.output_holdout}")
    print("\nNote: review rows are mapped labels, not final human-confirmed gold labels yet.")


if __name__ == "__main__":
    main()
