#!/usr/bin/env python3
"""
Skill Dataset Builder - 构建 SkillRouter 训练集

合并 synthetic_data.jsonl 和 real_data.jsonl，
使用 LLM Judge 标注质量，过滤低质量样本，输出最终训练集。

用法：
    python core/dataset_builder.py --synthetic synthetic_data.jsonl --real real_data.jsonl --output training_data.jsonl

依赖：
    pip install tqdm
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from tqdm import tqdm

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from core.utils import load_jsonl, save_jsonl


def merge_datasets(
    synthetic_data: List[Dict],
    real_data: List[Dict],
) -> List[Dict]:
    """
    合并合成数据和真实数据。

    Args:
        synthetic_data: 合成数据（Phase A）
        real_data: 真实数据（Phase B）

    Returns:
        合并后的数据集
    """
    merged = []

    for item in synthetic_data:
        merged.append({
            **item,
            "data_source": "synthetic",
        })

    for item in real_data:
        merged.append({
            **item,
            "data_source": "real",
        })

    return merged


def filter_by_quality(
    data: List[Dict],
    min_score: float = 0.7,
    max_token_waste_ratio: float = 0.25,
) -> List[Dict]:
    """
    根据质量过滤样本。

    过滤条件：
    1. judge_score >= min_score（只保留高质量样本）
    2. token_waste_ratio < max_token_waste_ratio（排除 token 浪费的样本）

    Args:
        data: 输入数据
        min_score: 最低分数阈值
        max_token_waste_ratio: 最高 token 浪费率阈值

    Returns:
        过滤后的数据
    """
    filtered = []
    for item in data:
        score = item.get("selection_score", item.get("judge", {}).get("selection_score", 0.5))
        waste = item.get("token_waste_ratio", item.get("token_efficiency", item.get("judge", {}).get("token_waste_ratio", 0.5)))

        if score >= min_score and waste < max_token_waste_ratio:
            filtered.append(item)

    return filtered


def build_skill_index(data: List[Dict]) -> Dict[str, int]:
    """
    构建 skill 索引（skill name -> index）。

    Args:
        data: 训练数据

    Returns:
        skill 索引字典
    """
    all_skills = set()
    for item in data:
        for skill in item.get("ideal_skills", []):
            all_skills.add(skill)
        for skill in item.get("selected_skills", []):
            all_skills.add(skill)

    skill_index = {skill: idx for idx, skill in enumerate(sorted(all_skills))}
    return skill_index


def prepare_training_format(
    data: List[Dict],
    skill_index: Dict[str, int],
) -> List[Dict]:
    """
    将数据转换为训练格式。

    输出格式：
    [
      {
        "user_message": "...",
        "ideal_skills": ["skill-a", "skill-b"],
        "skill_labels": [1, 1, 0, 0, ...],
        "score": 0.9,
        "token_efficiency": 0.12
      },
      ...
    ]

    Args:
        data: 输入数据
        skill_index: skill 索引

    Returns:
        训练格式数据
    """
    training_data = []

    for item in data:
        ideal_skills = item.get("ideal_skills", [])
        if not ideal_skills:
            ideal_skills = item.get("judge", {}).get("correct_skills", [])
        if not ideal_skills:
            ideal_skills = item.get("selected_skills", [])

        skill_labels = [0] * len(skill_index)
        for skill in ideal_skills:
            if skill in skill_index:
                skill_labels[skill_index[skill]] = 1

        training_data.append({
            "user_message": item.get("user_message", ""),
            "ideal_skills": ideal_skills,
            "skill_labels": skill_labels,
            "score": item.get("selection_score", 0.5),
            "token_efficiency": item.get("token_waste_ratio", item.get("token_efficiency", 0.5)),
            "data_source": item.get("data_source", "unknown"),
        })

    return training_data


def build_dataset(
    synthetic_path: str,
    real_path: str,
    output_path: str,
    min_score: float = 0.7,
    max_token_waste_ratio: float = 0.25,
):
    """
    构建完整训练集。

    Args:
        synthetic_path: 合成数据路径
        real_path: 真实数据路径
        output_path: 输出路径
        min_score: 最低分数阈值
        max_token_waste_ratio: 最高 token 浪费率阈值
    """
    print(f"\n开始构建训练集...")

    synthetic_data = load_jsonl(synthetic_path)
    real_data = load_jsonl(real_path)
    print(f"  合成数据: {len(synthetic_data)} 条")
    print(f"  真实数据: {len(real_data)} 条")

    merged_data = merge_datasets(synthetic_data, real_data)
    print(f"  合并后: {len(merged_data)} 条")

    filtered_data = filter_by_quality(
        merged_data,
        min_score=min_score,
        max_token_waste_ratio=max_token_waste_ratio,
    )
    print(f"  过滤后（score >= {min_score}, waste_ratio < {max_token_waste_ratio}）: {len(filtered_data)} 条")

    if not filtered_data:
        print("\n警告: 没有通过质量过滤的样本！")
        print("请检查：")
        print("  1. 是否已运行 core/judge.py 进行标注")
        print("  2. 是否需要调整 min_score 或 max_token_waste_ratio 阈值")
        return

    skill_index = build_skill_index(filtered_data)
    print(f"  Skill 数量: {len(skill_index)}")

    training_data = prepare_training_format(filtered_data, skill_index)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    save_jsonl(training_data, str(output_path))

    skill_index_path = output_path.parent / "skill_index.json"
    with open(skill_index_path, "w", encoding="utf-8") as f:
        json.dump(skill_index, f, ensure_ascii=False, indent=2)

    print(f"\n构建完成!")
    print(f"  最终训练集: {len(training_data)} 条")
    print(f"  保存到: {output_path}")
    print(f"  Skill 索引保存到: {skill_index_path}")

    sources = {}
    for item in training_data:
        source = item.get("data_source", "unknown")
        sources[source] = sources.get(source, 0) + 1

    print(f"\n数据来源分布:")
    for source, count in sources.items():
        print(f"  {source}: {count}")

    scores = [item.get("score", 0) for item in training_data]
    print(f"\n评分统计:")
    print(f"  平均分: {sum(scores) / len(scores):.3f}")
    print(f"  最高分: {max(scores):.3f}")
    print(f"  最低分: {min(scores):.3f}")


def main():
    parser = argparse.ArgumentParser(description="构建 SkillRouter 训练集")
    parser.add_argument(
        "--synthetic",
        required=True,
        help="合成数据路径",
    )
    parser.add_argument(
        "--real",
        default="",
        help="真实数据路径（可选）",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="输出文件路径",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.7,
        help="最低分数阈值（默认: 0.7）",
    )
    parser.add_argument(
        "--max-token-waste-ratio",
        type=float,
        default=0.25,
        help="最高 token 浪费率阈值（默认: 0.25）",
    )

    args = parser.parse_args()

    build_dataset(
        synthetic_path=args.synthetic,
        real_path=args.real,
        output_path=args.output,
        min_score=args.min_score,
        max_token_waste_ratio=args.max_token_waste_ratio,
    )


if __name__ == "__main__":
    main()
