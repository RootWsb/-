#!/usr/bin/env python3
"""
SkillRouter 训练脚本

训练 SkillRouter 分类器：冻结的 Qwen3-Embedding-0.6B + 可训练的 MLP 分类头。

用法：
    python core/train.py --data training_data.jsonl --output checkpoints/skill_router

前置条件：
    1. 先用 adapters 生成合成数据
    2. 运行 core/judge.py 进行质量标注
    3. 运行 core/dataset_builder.py 构建训练集

依赖：
    pip install torch transformers tqdm scikit-learn
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from core.model import SkillRouter
from core.utils import load_jsonl


# ============================================
# 数据集
# ============================================

class SkillSelectionDataset(Dataset):
    """
    Skill 选择训练数据集。

    数据格式：
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
    """

    def __init__(
        self,
        data: List[Dict],
        tokenizer,
        max_length: int = 512,
    ):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]

        encoding = self.tokenizer(
            item["user_message"],
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )

        input_ids = encoding["input_ids"].squeeze(0)
        attention_mask = encoding["attention_mask"].squeeze(0)
        labels = torch.tensor(item["skill_labels"], dtype=torch.float32)

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


# ============================================
# 训练函数
# ============================================

def compute_metrics(predictions, labels, threshold=0.5):
    """
    计算 skill 选择的评估指标。

    Args:
        predictions: 模型输出的概率 [batch, num_skills]
        labels: 真实标签 [batch, num_skills]
        threshold: 二分类阈值

    Returns:
        包含各项指标的字典
    """
    pred_binary = (predictions > threshold).float()

    element_accuracy = (pred_binary == labels).float().mean().item()

    batch_size = labels.shape[0]
    precisions = []
    recalls = []
    f1s = []

    for i in range(batch_size):
        pred_set = set(pred_binary[i].nonzero(as_tuple=True)[0].tolist())
        label_set = set(labels[i].nonzero(as_tuple=True)[0].tolist())

        if len(pred_set) == 0:
            precision = 0.0
        else:
            precision = len(pred_set & label_set) / len(pred_set)

        if len(label_set) == 0:
            recall = 0.0
        else:
            recall = len(pred_set & label_set) / len(label_set)

        precisions.append(precision)
        recalls.append(recall)

        if precision + recall > 0:
            f1s.append(2 * precision * recall / (precision + recall))
        else:
            f1s.append(0.0)

    recall_at_3 = 0
    for i in range(batch_size):
        top_k = min(3, predictions.shape[1])
        top_indices = predictions[i].topk(top_k).indices.tolist()
        label_indices = labels[i].nonzero(as_tuple=True)[0].tolist()
        if any(idx in label_indices for idx in top_indices):
            recall_at_3 += 1
    recall_at_3 /= batch_size

    precision_at_3 = 0
    for i in range(batch_size):
        top_k = min(3, predictions.shape[1])
        top_indices = predictions[i].topk(top_k).indices.tolist()
        label_indices = labels[i].nonzero(as_tuple=True)[0].tolist()
        correct_in_top3 = len(set(top_indices) & set(label_indices))
        precision_at_3 += correct_in_top3 / top_k
    precision_at_3 /= batch_size

    return {
        "element_accuracy": element_accuracy,
        "mean_precision": sum(precisions) / len(precisions),
        "mean_recall": sum(recalls) / len(recalls),
        "mean_f1": sum(f1s) / len(f1s),
        "recall_at_3": recall_at_3,
        "precision_at_3": precision_at_3,
    }


def load_training_data(data_path: str) -> Tuple[List[Dict], Dict[str, int]]:
    """
    加载训练数据和 skill 索引。

    Args:
        data_path: 训练数据路径

    Returns:
        (data, skill_index)
    """
    data = load_jsonl(data_path)

    skill_index_path = Path(data_path).parent / "skill_index.json"
    if skill_index_path.exists():
        with open(skill_index_path, "r", encoding="utf-8") as f:
            skill_index = json.load(f)
    else:
        all_skills = set()
        for item in data:
            for skill in item.get("ideal_skills", []):
                all_skills.add(skill)
        skill_index = {skill: idx for idx, skill in enumerate(sorted(all_skills))}

    return data, skill_index


def train_model(
    model: SkillRouter,
    train_data: List[Dict],
    val_data: Optional[List[Dict]] = None,
    output_dir: str = "checkpoints/skill_router",
    num_epochs: int = 10,
    batch_size: int = 32,
    learning_rate: float = 1e-4,
    weight_decay: float = 0.01,
    warmup_steps: int = 100,
    device: Optional[str] = None,
    skill_index: Optional[Dict[str, int]] = None,
):
    """
    训练 SkillRouter 模型。

    Args:
        model: SkillRouter 模型
        train_data: 训练数据
        val_data: 验证数据（可选）
        output_dir: 输出目录
        num_epochs: 训练轮数
        batch_size: 批次大小
        learning_rate: 学习率
        weight_decay: 权重衰减
        warmup_steps: 预热步数
        device: 设备
        skill_index: skill 索引（用于计算评估指标）
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")

    model = model.to(device)

    # 计算正负样本权重，处理类别不平衡
    all_labels = [item["skill_labels"] for item in train_data]
    pos_counts = [0] * len(all_labels[0])
    for labels in all_labels:
        for i, v in enumerate(labels):
            if v == 1:
                pos_counts[i] += 1
    num_samples = len(train_data)
    pos_weight = [
        max(1.0, (num_samples - c) / max(1, c))
        for c in pos_counts
    ]
    pos_weight_tensor = torch.tensor(pos_weight, dtype=torch.float32).to(device)
    print(f"  Pos weight 范围: [{min(pos_weight):.1f}, {max(pos_weight):.1f}]")

    train_dataset = SkillSelectionDataset(
        train_data,
        model.tokenizer,
        max_length=512,
    )
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
    )

    val_loader = None
    if val_data:
        val_dataset = SkillSelectionDataset(
            val_data,
            model.tokenizer,
            max_length=512,
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=0,
        )

    optimizer = torch.optim.AdamW(
        model.classifier.parameters(),
        lr=learning_rate,
        weight_decay=weight_decay,
    )

    total_steps = len(train_loader) * num_epochs
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=learning_rate,
        total_steps=total_steps,
        pct_start=warmup_steps / total_steps if warmup_steps < total_steps else 0.1,
    )

    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight_tensor)

    best_val_loss = float("inf")
    history = []
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n开始训练...")
    print(f"  训练集大小: {len(train_data)}")
    if val_data:
        print(f"  验证集大小: {len(val_data)}")
    print(f"  Epochs: {num_epochs}")
    print(f"  Batch size: {batch_size}")
    print(f"  Learning rate: {learning_rate}")
    print()

    for epoch in range(num_epochs):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs}")
        for batch in pbar:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            logits = model(input_ids, attention_mask)
            loss = criterion(logits, labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            scheduler.step()

            train_loss += loss.item()
            predictions = (torch.sigmoid(logits) > 0.5).float()
            train_correct += (predictions == labels).sum().item()
            train_total += labels.numel()

            pbar.set_postfix({
                "loss": f"{loss.item():.4f}",
                "lr": f"{scheduler.get_last_lr()[0]:.6f}",
            })

        train_loss /= len(train_loader)
        train_accuracy = train_correct / train_total

        val_loss = 0.0
        val_accuracy = 0.0
        val_metrics = {}
        if val_loader:
            model.eval()
            val_correct = 0
            val_total = 0
            all_preds = []
            all_labels = []

            with torch.no_grad():
                for batch in val_loader:
                    input_ids = batch["input_ids"].to(device)
                    attention_mask = batch["attention_mask"].to(device)
                    labels = batch["labels"].to(device)

                    logits = model(input_ids, attention_mask)
                    loss = criterion(logits, labels)

                    val_loss += loss.item()
                    predictions = (torch.sigmoid(logits) > 0.5).float()
                    val_correct += (predictions == labels).sum().item()
                    val_total += labels.numel()

                    all_preds.append(torch.sigmoid(logits).cpu())
                    all_labels.append(labels.cpu())

            val_loss /= len(val_loader)
            val_accuracy = val_correct / val_total

            all_preds = torch.cat(all_preds, dim=0)
            all_labels = torch.cat(all_labels, dim=0)
            val_metrics = compute_metrics(all_preds, all_labels)

        print(
            f"Epoch {epoch+1}/{num_epochs}: "
            f"train_loss={train_loss:.4f}, train_acc={train_accuracy:.4f}"
        )
        if val_loader:
            print(f"  val_loss={val_loss:.4f}, val_acc={val_accuracy:.4f}")

        history.append({
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "train_accuracy": train_accuracy,
            "val_loss": val_loss if val_loader else None,
            "val_accuracy": val_accuracy if val_loader else None,
            "val_metrics": val_metrics if val_metrics else None,
        })

        if val_loader and val_loss < best_val_loss:
            best_val_loss = val_loss
            model.save_classifier(output_dir / "best")
            print(f"  OK 保存最佳模型 (val_loss={val_loss:.4f})")
        elif not val_loader and epoch == num_epochs - 1:
            model.save_classifier(output_dir / "best")

    model.save_classifier(output_dir / "final")

    stats = {
        "num_epochs": num_epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "train_size": len(train_data),
        "val_size": len(val_data) if val_data else 0,
        "best_val_loss": best_val_loss if val_loader else None,
        "final_train_loss": train_loss,
        "final_train_accuracy": train_accuracy,
        "final_val_metrics": val_metrics if val_metrics else None,
        "history": history,
    }
    with open(output_dir / "training_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"\n训练完成!")
    print(f"  最佳模型保存到: {output_dir / 'best'}")
    print(f"  最终模型保存到: {output_dir / 'final'}")
    print(f"  训练统计保存到: {output_dir / 'training_stats.json'}")


# ============================================
# 主函数
# ============================================

def main():
    parser = argparse.ArgumentParser(description="SkillRouter 训练脚本")
    parser.add_argument(
        "--data",
        required=True,
        help="训练数据路径",
    )
    parser.add_argument(
        "--output",
        default="checkpoints/skill_router",
        help="输出目录（默认: checkpoints/skill_router）",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="训练轮数（默认: 10）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="批次大小（默认: 32）",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=1e-4,
        help="学习率（默认: 1e-4）",
    )
    parser.add_argument(
        "--val-split",
        type=float,
        default=0.1,
        help="验证集比例（默认: 0.1）",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="设备（默认: auto）",
    )
    parser.add_argument(
        "--embedding-model",
        default="Qwen/Qwen3-Embedding-0.6B",
        help="Embedding model name or local path.",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Hugging Face cache directory.",
    )
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Load embedding model only from local files/cache.",
    )

    args = parser.parse_args()

    if not os.path.exists(args.data):
        print(f"错误: 训练数据文件不存在: {args.data}")
        print("请先运行 dataset_builder.py 构建训练集")
        return

    print(f"加载训练数据: {args.data}")
    data, skill_index = load_training_data(args.data)
    print(f"  数据量: {len(data)} 条")
    print(f"  Skill 数量: {len(skill_index)}")

    import random
    random.seed(42)
    random.shuffle(data)

    split_idx = int(len(data) * (1 - args.val_split))
    train_data = data[:split_idx]
    val_data = data[split_idx:]

    print(f"  训练集: {len(train_data)} 条")
    print(f"  验证集: {len(val_data)} 条")

    model = SkillRouter(
        num_skills=len(skill_index),
        embedding_model=args.embedding_model,
        cache_dir=args.cache_dir,
        local_files_only=args.local_files_only,
    )

    train_model(
        model=model,
        train_data=train_data,
        val_data=val_data,
        output_dir=args.output,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        device=args.device,
        skill_index=skill_index,
    )


if __name__ == "__main__":
    main()
