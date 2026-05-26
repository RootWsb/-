#!/usr/bin/env python3
"""
Create weak/silver labels for Tianleixia log candidates.

The rules are intentionally conservative and transparent. They are meant for
bulk smoke testing and triage, not as final ground-truth labels.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))


NO_SKILL_EXACT = {
    "ok",
    "确认",
    "可以",
    "认可",
    "推送",
    "重试一下",
    "请再试一试",
    "hi",
    "你好",
    "你好，你是谁",
    "1",
    "a",
    "b",
}


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


def load_valid_skills(catalog_path: Path) -> set:
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    return {item["skill_name"] for item in catalog}


def has_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def looks_like_context_only(text: str) -> bool:
    normalized = " ".join(text.strip().lower().split())
    if normalized in NO_SKILL_EXACT:
        return True
    if re.fullmatch(r"[\w\-.]+", normalized or "") and len(normalized) <= 12:
        return True
    if re.fullmatch(r"(https?://\S+\s*)?(token[:：]?\s*)?[\w\-]{8,}", normalized):
        return True
    if has_any(normalized, ["api", "apibase", "token", "端口", "开放端口", "网段"]) and len(normalized) < 80:
        return True
    return False


def auto_label(row: Dict) -> Tuple[List[str], str, str]:
    message = row.get("user_message", "")
    text = " ".join(message.lower().split())
    workspace = (row.get("workspace_name") or "").lower()
    agents = set(row.get("observed_agents") or [])

    if looks_like_context_only(message):
        return [], "high", "上下文补充、确认、短回复或环境信息，单独看不应触发 skill。"

    skills = set()
    reasons = []

    oa_terms = [
        "万象", "oa", "nocobase", "数据表", "数据源", "工作流", "页面", "区块",
        "字段", "表格", "菜单", "插件", "导入", "导出", "审批", "供应商",
        "供应项", "分类视图", "权限", "oracle", "mssql", "kingbase", "外部数据源",
        "腾讯", "抖音", "线索", "业务合同", "全局项目",
    ]
    if has_any(text + " " + workspace, oa_terms) or any(a.startswith("oa-") for a in agents):
        skills.add("wanxiangoa-api")
        reasons.append("涉及万象/OA/NocoBase 的数据建模、页面、工作流、插件或配置操作。")

    unclear_terms = [
        "需求", "还没想好", "怎么实现", "帮我实现", "设计", "方案", "规划",
        "分析", "区别", "优化", "全方面", "复杂一点", "功能", "要求",
    ]
    if has_any(text, unclear_terms):
        skills.add("requirements-clarifier")
        reasons.append("需要澄清目标、范围、验收标准或把需求整理成可执行任务。")

    research_terms = [
        "官网", "官方", "文档", "对比", "区别", "分析", "调研", "分解",
        "优化空间", "全面分解", "深度剖析",
    ]
    if has_any(text, research_terms):
        skills.add("materials-to-problems")
        reasons.append("需要基于材料/官网/现状做问题定义或差异分析。")

    code_terms = [
        "python", "web应用", "html", "页面返回", "公网ip", "原生http",
        "代码", "分支", "仓库", "git", "克隆", "拉取", "开发", "修改",
    ]
    if has_any(text, code_terms):
        skills.add("writing-plans")
        reasons.append("涉及代码/分支/实现任务，通常需要先形成实现计划。")
        if has_any(text, ["实现", "开发", "修改", "修复", "web应用", "html", "python"]):
            skills.add("test-driven-development")
            reasons.append("涉及实现或修复，按当前 skill 边界可用 TDD 约束开发。")

    debug_terms = [
        "报错", "错误", "失败", "不显示", "不能", "无法", "问题", "排查",
        "修复", "bug", "traceback", "connectionrefused", "timeout",
    ]
    if has_any(text, debug_terms):
        skills.add("systematic-debugging")
        reasons.append("涉及失败、异常或问题定位。")

    test_terms = ["测试", "验收", "自检", "是否满足", "验证", "检查"]
    if has_any(text, test_terms):
        if has_any(text, ["测试用例", "用例"]):
            skills.add("requirements-to-test-cases")
            reasons.append("请求把需求转为测试用例。")
        else:
            skills.add("execute-test-cases")
            reasons.append("请求执行测试、自检、验收或验证。")

    plan_terms = ["执行计划", "任务计划", "按计划", "继续执行"]
    if has_any(text, plan_terms):
        skills.add("executing-plans")
        reasons.append("请求执行已有计划。")

    parallel_terms = ["分别", "并行", "多个", "同时"]
    if has_any(text, parallel_terms) and has_any(text, ["任务", "模块", "插件", "页面"]):
        skills.add("dispatching-parallel-agents")
        reasons.append("存在多个相对独立任务，可能适合并行分派。")

    if not skills:
        return [], "medium", "未命中明确 skill 触发条件，暂按无 skill 处理。"

    ordered = [
        "requirements-clarifier",
        "materials-to-problems",
        "wanxiangoa-api",
        "writing-plans",
        "test-driven-development",
        "systematic-debugging",
        "requirements-to-test-cases",
        "execute-test-cases",
        "executing-plans",
        "dispatching-parallel-agents",
    ]
    labeled = [skill for skill in ordered if skill in skills]
    confidence = "medium"
    if len(labeled) <= 2 and ("wanxiangoa-api" in labeled or "systematic-debugging" in labeled):
        confidence = "high"
    if len(labeled) >= 4:
        confidence = "low"
    return labeled[:5], confidence, "；".join(reasons)


def main():
    parser = argparse.ArgumentParser(description="Auto-label Tianleixia log candidates.")
    parser.add_argument(
        "--input",
        default=str(PACKAGE_ROOT / "data" / "tianleixia_log_candidates.jsonl"),
    )
    parser.add_argument(
        "--output",
        default=str(PACKAGE_ROOT / "data" / "tianleixia_log_silver.jsonl"),
    )
    parser.add_argument(
        "--catalog",
        default=str(PACKAGE_ROOT / "data" / "skill_catalog.json"),
    )
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    valid = load_valid_skills(Path(args.catalog))
    labeled = []
    for row in rows:
        skills, confidence, reason = auto_label(row)
        unknown = [skill for skill in skills if skill not in valid]
        if unknown:
            raise ValueError(f"Unknown skills generated: {unknown}")
        labeled.append({
            **row,
            "ideal_skills": skills,
            "source": "tianleixia_log_silver",
            "label_confidence": confidence,
            "label_reason": reason,
        })

    save_jsonl(labeled, Path(args.output))

    counts = {}
    for row in labeled:
        for skill in row["ideal_skills"]:
            counts[skill] = counts.get(skill, 0) + 1
    print(f"input_rows: {len(rows)}")
    print(f"output: {args.output}")
    print(f"zero_skill_rows: {sum(1 for row in labeled if not row['ideal_skills'])}")
    print("top_skills:")
    for skill, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:20]:
        print(f"  {skill}: {count}")


if __name__ == "__main__":
    main()
