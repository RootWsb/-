#!/usr/bin/env python3
"""
模拟 Legacy 关键词路由系统，生成对比数据。

Legacy 系统行为：对每条用户消息，用简单的关键词匹配选出所有可能相关的 skills，
然后由 LLM Judge 评估选择质量 → selection_score + token_waste_ratio。

这模拟了当前天磊虾全量挂载所有 skill 的低效做法。

用法：
    python scripts\\simulate_legacy.py --input data\\synthetic_data.jsonl --output data\\legacy_data.jsonl
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from core.utils import load_jsonl, save_jsonl


def build_keyword_map(catalog: List[Dict]) -> Dict[str, List[str]]:
    """为每个 skill 构建关键词列表（从 description 和 when_to_use 提取）"""
    keyword_map: Dict[str, List[str]] = {}
    for skill in catalog:
        name = skill["skill_name"]
        text = (skill.get("description", "") + " " + skill.get("when_to_use", "")).lower()
        # 提取中文关键词（2-6 字）和英文单词
        cn_keywords = re.findall(r'[一-鿿]{2,6}', text)
        en_keywords = [w for w in re.findall(r'[a-zA-Z]{3,}', text) if len(w) > 3]
        keyword_map[name] = list(set(cn_keywords + en_keywords))[:20]
    return keyword_map


def legacy_keyword_match(
    user_message: str,
    keyword_map: Dict[str, List[str]],
    threshold: int = 1,
) -> List[str]:
    """Legacy 系统：关键词匹配，命中 >= threshold 个关键词就选中 skill"""
    msg_lower = user_message.lower()
    selected = []
    for skill_name, keywords in keyword_map.items():
        hits = sum(1 for kw in keywords if kw in msg_lower)
        if hits >= threshold:
            selected.append(skill_name)
    return selected


def simulate_legacy_system(
    data: List[Dict],
    catalog: List[Dict],
) -> List[Dict]:
    """模拟 Legacy 系统行为：关键词匹配 → Judge 评估"""
    keyword_map = build_keyword_map(catalog)
    results = []

    for item in data:
        user_message = item.get("user_message", "")
        selected_skills = legacy_keyword_match(user_message, keyword_map)
        ideal_skills = item.get("ideal_skills", [])

        # 计算 selection_score（F1）
        selected_set = set(selected_skills)
        ideal_set = set(ideal_skills)

        if ideal_set:
            precision = len(selected_set & ideal_set) / max(1, len(selected_set))
            recall = len(selected_set & ideal_set) / len(ideal_set)
            if precision + recall > 0:
                selection_score = 2 * precision * recall / (precision + recall)
            else:
                selection_score = 0.0
        else:
            # 没有理想 skill 时，选多了扣分
            selection_score = 1.0 if not selected_set else max(0.0, 1.0 - 0.15 * len(selected_set))

        # token_waste_ratio
        unnecessary = selected_set - ideal_set
        token_waste_ratio = len(unnecessary) / max(1, len(selected_skills))

        results.append({
            "user_message": user_message,
            "selected_skills": sorted(selected_skills),
            "ideal_skills": ideal_skills,
            "selection_score": round(selection_score, 3),
            "token_waste_ratio": round(token_waste_ratio, 3),
            "source": item.get("source", ""),
            "generation_method": "legacy_simulation",
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="模拟 Legacy 关键词路由系统")
    parser.add_argument("--input", required=True, help="输入数据路径（synthetic_data.jsonl）")
    parser.add_argument("--output", required=True, help="输出数据路径")
    parser.add_argument(
        "--skill-catalog",
        default=str(PACKAGE_ROOT / "data" / "skill_catalog.json"),
        help="Skill catalog path.",
    )
    args = parser.parse_args()

    skill_catalog_path = Path(args.skill_catalog)
    with open(skill_catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    print(f"加载数据: {args.input}")
    data = load_jsonl(args.input)
    print(f"  共 {len(data)} 条")
    print(f"  Skill catalog: {len(catalog)} 个 skill")

    print(f"\n模拟 Legacy 关键词路由系统...")
    results = simulate_legacy_system(data, catalog)

    # 统计
    total_selected = sum(len(r["selected_skills"]) for r in results)
    total_ideal = sum(len(r["ideal_skills"]) for r in results)
    avg_selected = total_selected / len(results) if results else 0
    avg_ideal = total_ideal / len(results) if results else 0

    scores = [r["selection_score"] for r in results]
    avg_score = sum(scores) / len(scores) if scores else 0
    waste = [r["token_waste_ratio"] for r in results]
    avg_waste = sum(waste) / len(waste) if waste else 0

    print(f"\nLegacy 系统模拟结果:")
    print(f"  总样本数: {len(results)}")
    print(f"  平均选中 skill 数: {avg_selected:.2f}（ML 目标: {avg_ideal:.2f}）")
    print(f"  平均 selection_score: {avg_score:.3f}")
    print(f"  平均 token_waste_ratio: {avg_waste:.3f}")

    save_jsonl(results, args.output)
    print(f"\n保存到: {args.output}")


if __name__ == "__main__":
    main()
