#!/usr/bin/env python3
"""
SkillRouter 模型定义

轻量 skill 路由器：冻结的 Qwen3-Embedding-0.6B + 可训练的 MLP 分类头。

架构：
    用户消息 → Qwen3-Embedding-0.6B (冻结) → 语义向量 → MLP 分类头 (可训练) → Top-K skills

资源占用：
    - 训练显存：~8GB（embedding 模型冻结）
    - 分类头大小：几 MB
    - 推理时间：<10ms（CPU 即可）

用法：
    from core.model import SkillRouter
    router = SkillRouter(num_skills=37)
    results = router.predict("帮我看看最近有什么新的 AI 论文", top_k=5)
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer


class SkillRouter(nn.Module):
    """
    轻量 skill 路由器：冻结的 Embedding + 可训练的 MLP 分类头。
    """

    def __init__(
        self,
        num_skills: int,
        embedding_model: str = "Qwen/Qwen3-Embedding-0.6B",
        hidden_dim: int = 256,
        dropout: float = 0.1,
        cache_dir: Optional[str] = None,
        local_files_only: bool = False,
    ):
        """
        初始化 SkillRouter。

        Args:
            num_skills: skill 数量（必须指定）
            embedding_model: embedding 模型名称或路径
            hidden_dim: MLP 隐藏层维度
            dropout: dropout 比率
            cache_dir: Hugging Face 缓存目录（可选）
            local_files_only: 只从本地缓存/路径加载，不联网
        """
        super().__init__()

        self.num_skills = num_skills
        self.embedding_model_name = embedding_model

        # 1. 编码器：Qwen3-Embedding-0.6B（冻结，不训练）
        print(f"加载 embedding 模型: {embedding_model}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            embedding_model,
            trust_remote_code=True,
            cache_dir=cache_dir,
            local_files_only=local_files_only,
        )
        self.encoder = AutoModel.from_pretrained(
            embedding_model,
            trust_remote_code=True,
            cache_dir=cache_dir,
            local_files_only=local_files_only,
        )

        # 冻结 encoder 参数
        for param in self.encoder.parameters():
            param.requires_grad = False

        # 2. 分类头：MLP（只有几 MB，可训练）
        embed_dim = self.encoder.config.hidden_size  # 1024 for Qwen3-Embedding-0.6B
        self.classifier = nn.Sequential(
            nn.Linear(embed_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_skills),
        )
        # bias 初始化为正值，避免 Sigmoid 初始输出全接近 0
        with torch.no_grad():
            self.classifier[-1].bias.fill_(1.0)

        print(f"模型初始化完成:")
        print(f"  Embedding 维度: {embed_dim}")
        print(f"  Skill 数量: {num_skills}")
        print(f"  分类头参数: {sum(p.numel() for p in self.classifier.parameters()):,}")

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        前向传播。

        Args:
            input_ids: 输入 token IDs [batch, seq_len]
            attention_mask: 注意力掩码 [batch, seq_len]

        Returns:
            logits: skill 分数 [batch, num_skills]
        """
        with torch.no_grad():
            outputs = self.encoder(
                input_ids=input_ids,
                attention_mask=attention_mask,
            )
            hidden = outputs.last_hidden_state.mean(dim=1)  # mean pooling [batch, embed_dim]

        logits = self.classifier(hidden)  # [batch, num_skills]
        return logits

    def predict(
        self,
        text: str,
        skill_names: List[str],
        top_k: int = 5,
        threshold: float = 0.3,
        sigmoid: bool = True,
    ) -> List[Dict]:
        """
        预测最相关的 top-k skills。

        Args:
            text: 用户消息
            skill_names: skill 名称列表
            top_k: 返回 top-k 个结果
            threshold: 最低分数阈值
            sigmoid: 是否对输出做 sigmoid（True=分类模式，False=原始 logits）

        Returns:
            [{"skill": "skill-name", "score": 0.95}, ...]
        """
        self.eval()

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        device = next(self.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}

        with torch.no_grad():
            logits = self.forward(**inputs).squeeze(0)  # [num_skills]
            if sigmoid:
                scores = torch.sigmoid(logits)
            else:
                scores = logits

        top_k = min(top_k, len(skill_names))
        top_indices = scores.topk(top_k).indices

        results = []
        for idx in top_indices:
            skill_name = skill_names[idx.item()]
            score = scores[idx].item()
            if score >= threshold:
                results.append({
                    "skill": skill_name,
                    "score": round(score, 4),
                })

        return results

    def save_classifier(self, save_dir: str):
        """
        保存分类头权重。

        Args:
            save_dir: 保存目录
        """
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        torch.save(
            self.classifier.state_dict(),
            save_dir / "classifier.pt",
        )

        config = {
            "num_skills": self.num_skills,
            "embedding_model": self.embedding_model_name,
            "hidden_dim": self.classifier[0].out_features,
            "dropout": self.classifier[2].p if len(self.classifier) > 2 else 0.1,
        }
        with open(save_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        print(f"分类头权重保存到: {save_dir}")

    @classmethod
    def load_classifier(
        cls,
        load_dir: str,
        device: Optional[str] = None,
        embedding_model: Optional[str] = None,
        cache_dir: Optional[str] = None,
        local_files_only: bool = False,
    ) -> "SkillRouter":
        """
        加载训练好的分类器。

        Args:
            load_dir: 加载目录
            device: 设备（'cpu' 或 'cuda'）

        Returns:
            SkillRouter 实例
        """
        load_dir = Path(load_dir)

        with open(load_dir / "config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        model = cls(
            num_skills=config["num_skills"],
            embedding_model=embedding_model or config["embedding_model"],
            hidden_dim=config["hidden_dim"],
            dropout=config.get("dropout", 0.1),
            cache_dir=cache_dir,
            local_files_only=local_files_only,
        )

        classifier_path = load_dir / "classifier.pt"
        if classifier_path.exists():
            state_dict = torch.load(classifier_path, map_location=device or "cpu")
            model.classifier.load_state_dict(state_dict)
            print(f"分类头权重加载成功: {classifier_path}")
        else:
            print(f"警告: 分类头权重文件不存在: {classifier_path}")

        if device:
            model = model.to(device)

        return model

    def freeze_encoder(self):
        """冻结 encoder 参数（训练时使用）"""
        for param in self.encoder.parameters():
            param.requires_grad = False

    def unfreeze_encoder(self):
        """解冻 encoder 参数（微调时使用，谨慎使用）"""
        for param in self.encoder.parameters():
            param.requires_grad = True

    def get_param_stats(self) -> Dict:
        """
        获取参数统计信息。

        Returns:
            参数统计字典
        """
        total_params = sum(p.numel() for p in self.parameters())
        trainable_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        encoder_params = sum(p.numel() for p in self.encoder.parameters())
        classifier_params = sum(p.numel() for p in self.classifier.parameters())

        return {
            "total_params": total_params,
            "trainable_params": trainable_params,
            "frozen_params": total_params - trainable_params,
            "encoder_params": encoder_params,
            "classifier_params": classifier_params,
            "trainable_ratio": trainable_params / total_params if total_params > 0 else 0,
        }


def create_skill_router(
    skill_index_path: str,
    model_dir: Optional[str] = None,
    device: Optional[str] = None,
) -> SkillRouter:
    """
    创建 SkillRouter 实例（便捷函数）。

    Args:
        skill_index_path: skill 索引文件路径（skill_index.json）
        model_dir: 模型权重目录（如果为 None，创建新模型）
        device: 设备

    Returns:
        SkillRouter 实例
    """
    with open(skill_index_path, "r", encoding="utf-8") as f:
        skill_index = json.load(f)

    num_skills = len(skill_index)

    if model_dir and Path(model_dir).exists():
        model = SkillRouter.load_classifier(model_dir, device)
    else:
        model = SkillRouter(num_skills=num_skills)

    return model
