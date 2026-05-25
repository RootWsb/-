#!/usr/bin/env python3
"""
用训练好的 SkillRouter 模型评估 synthetic_data，生成 ML 系统的对比数据。
"""

import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

import torch
import json
import argparse
from core.model import SkillRouter
from core.utils import load_jsonl, save_jsonl

CKPT_DIR = str(PACKAGE_ROOT / "checkpoints" / "skill_router" / "best")
SKILL_INDEX_PATH = str(PACKAGE_ROOT / "data" / "skill_index.json")
INPUT_PATH = str(PACKAGE_ROOT / "data" / "synthetic_data.jsonl")
OUTPUT_PATH = str(PACKAGE_ROOT / "data" / "ml_data.jsonl")

parser = argparse.ArgumentParser(description="Evaluate trained SkillRouter.")
parser.add_argument("--checkpoint", default=CKPT_DIR)
parser.add_argument("--skill-index", default=SKILL_INDEX_PATH)
parser.add_argument("--input", default=INPUT_PATH)
parser.add_argument("--output", default=OUTPUT_PATH)
parser.add_argument("--threshold", type=float, default=0.5)
parser.add_argument("--top-k", type=int, default=5)
args = parser.parse_args()

print("加载 SkillRouter 模型...")
model = SkillRouter.load_classifier(args.checkpoint, device="cuda" if torch.cuda.is_available() else "cpu")

with open(args.skill_index, "r", encoding="utf-8") as f:
    skill_index = json.load(f)
skill_names = [name for name, _ in sorted(skill_index.items(), key=lambda item: item[1])]
print(f"  Skills: {len(skill_names)}")
print(f"  Threshold: {args.threshold}")
print(f"  Top-K: {args.top_k}")

data = load_jsonl(args.input)
print(f"  待评估样本: {len(data)}")

results = []
for item in data:
    msg = item.get("user_message", "")
    ideal = set(item.get("ideal_skills", []))

    preds = model.predict(msg, skill_names, top_k=args.top_k, threshold=args.threshold)
    selected = [p["skill"] for p in preds]
    selected_set = set(selected)

    if ideal:
        tp = len(selected_set & ideal)
        precision = tp / max(1, len(selected_set))
        recall = tp / len(ideal)
        score = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    else:
        score = 1.0 if not selected_set else max(0.0, 1.0 - 0.15 * len(selected_set))

    unnecessary = selected_set - ideal
    waste = len(unnecessary) / max(1, len(selected))

    results.append({
        "user_message": msg,
        "selected_skills": sorted(selected),
        "ideal_skills": sorted(ideal),
        "selection_score": round(score, 3),
        "token_waste_ratio": round(waste, 3),
        "source": item.get("source", ""),
        "generation_method": "ml_skillrouter",
    })

avg_score = sum(r["selection_score"] for r in results) / len(results) if results else 0
avg_waste = sum(r["token_waste_ratio"] for r in results) / len(results) if results else 0
avg_selected = sum(len(r["selected_skills"]) for r in results) / len(results) if results else 0
avg_ideal = sum(len(r["ideal_skills"]) for r in results) / len(results) if results else 0

print(f"\nML SkillRouter 评估结果:")
print(f"  平均选中 skill 数: {avg_selected:.2f}（理想: {avg_ideal:.2f}）")
print(f"  平均 selection_score: {avg_score:.3f}")
print(f"  平均 token_waste_ratio: {avg_waste:.3f}")

save_jsonl(results, args.output)
print(f"\n保存到: {args.output}")
