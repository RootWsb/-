#!/usr/bin/env python3
"""
Skill Router 可视化对比报告

生成 4 张 PNG 对比图，展示 Legacy 关键词路由 vs ML SkillRouter 的效果差异。

用法：
    python core/visualize.py --output-dir ./plots

前置条件：
    1. 已生成合成数据 / 收集真实数据
    2. 已运行 core/judge.py 进行质量标注
    3. 已运行 core/train.py 训练模型（生成 training_stats.json）

依赖：
    pip install matplotlib numpy
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from core.utils import load_jsonl


# ============================================
# 中文字体配置
# ============================================

def setup_chinese_font():
    """配置 matplotlib 中文字体"""
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False


# ============================================
# 数据加载
# ============================================

def load_training_stats(path: str) -> Optional[Dict]:
    """加载训练统计"""
    if not path or not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================
# 图 1: Skill 选择准确率对比（柱状图）
# ============================================

def plot_accuracy_comparison(
    legacy_data: List[Dict],
    ml_data: List[Dict],
    output_path: str,
):
    """对比 Legacy vs ML 的 selection_score"""
    legacy_scores = [item.get('selection_score', 0) for item in legacy_data]
    legacy_avg_score = np.mean(legacy_scores) if legacy_scores else 0

    ml_scores = [item.get('selection_score', 0) for item in ml_data]
    ml_avg_score = np.mean(ml_scores) if ml_scores else 0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    x = np.arange(1)
    width = 0.35

    bars1 = ax1.bar(x - width/2, [legacy_avg_score * 100], width, label='Legacy 关键词路由', color='#FF6B6B')
    bars2 = ax1.bar(x + width/2, [ml_avg_score * 100], width, label='ML SkillRouter', color='#4ECDC4')

    ax1.set_ylabel('准确率 (%)')
    ax1.set_title('Skill 选择准确率对比')
    ax1.set_xticks(x)
    ax1.set_xticklabels(['Selection Score'])
    ax1.legend()
    ax1.set_ylim(0, 100)

    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom')
    for bar in bars2:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom')

    bars3 = ax2.bar(x - width/2, [len(legacy_data)], width, label='Legacy', color='#FF6B6B')
    bars4 = ax2.bar(x + width/2, [len(ml_data)], width, label='ML', color='#4ECDC4')

    ax2.set_ylabel('样本数量')
    ax2.set_title('评估样本数量')
    ax2.set_xticks(x)
    ax2.set_xticklabels(['数据集'])
    ax2.legend()

    for bar in bars3:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}', ha='center', va='bottom')
    for bar in bars4:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}', ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  OK 图 1 已保存: {output_path}")


# ============================================
# 图 2: Token 浪费率分布（箱线图）
# ============================================

def plot_token_waste_distribution(
    legacy_data: List[Dict],
    ml_data: List[Dict],
    output_path: str,
):
    """对比 Legacy vs ML 的 token_waste_ratio 分布"""
    legacy_waste = [item.get('token_waste_ratio', 0) for item in legacy_data]
    ml_waste = [item.get('token_waste_ratio', 0) for item in ml_data]

    fig, ax = plt.subplots(figsize=(8, 5))

    data_to_plot = [legacy_waste, ml_waste]
    labels = ['Legacy 关键词路由', 'ML SkillRouter']

    bp = ax.boxplot(data_to_plot, tick_labels=labels, patch_artist=True)

    bp['boxes'][0].set_facecolor('#FF6B6B')
    bp['boxes'][1].set_facecolor('#4ECDC4')

    ax.set_ylabel('Token 浪费率')
    ax.set_title('Token 浪费率分布对比（越低越好）')
    ax.set_ylim(0, 1)

    for i, data in enumerate([legacy_waste, ml_waste]):
        if data:
            mean_val = np.mean(data)
            ax.text(i + 1, mean_val + 0.05, f'均值: {mean_val:.2f}',
                   ha='center', fontsize=10, color='black')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  OK 图 2 已保存: {output_path}")


# ============================================
# 图 3: 训练曲线（折线图）
# ============================================

def plot_training_curves(
    training_stats: Optional[Dict],
    output_path: str,
):
    """绘制训练曲线（Loss 和 Accuracy）"""
    if not training_stats:
        print("  X 无法绘制训练曲线: training_stats.json 不存在")
        return

    history = training_stats.get('history') or []
    if history:
        epochs = [item.get('epoch', i + 1) for i, item in enumerate(history)]
        train_losses = [item.get('train_loss', np.nan) for item in history]
        val_losses = [item.get('val_loss', np.nan) for item in history]
        train_accs = [item.get('train_accuracy', np.nan) for item in history]
        val_accs = [item.get('val_accuracy', np.nan) for item in history]
        loss_title = '训练损失曲线'
        acc_title = '训练准确率曲线'
    else:
        epoch = training_stats.get('num_epochs', 1)
        epochs = [epoch]
        train_losses = [training_stats.get('final_train_loss', np.nan)]
        val_losses = [training_stats.get('best_val_loss', np.nan)]
        train_accs = [training_stats.get('final_train_accuracy', np.nan)]
        final_val_metrics = training_stats.get('final_val_metrics') or {}
        val_accs = [final_val_metrics.get('element_accuracy', np.nan)]
        loss_title = '训练损失摘要'
        acc_title = '训练准确率摘要'

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    ax1.plot(epochs, train_losses, 'b-o', label='训练损失', markersize=4)
    ax1.plot(epochs, val_losses, 'r-s', label='验证损失', markersize=4)
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('BCE Loss')
    ax1.set_title(loss_title)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.plot(epochs, train_accs, 'b-o', label='训练准确率', markersize=4)
    ax2.plot(epochs, val_accs, 'r-s', label='验证准确率', markersize=4)
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('准确率')
    ax2.set_title(acc_title)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  OK 图 3 已保存: {output_path}")


# ============================================
# 图 4: Skill 选择数量对比（直方图）
# ============================================

def plot_skill_count_distribution(
    legacy_data: List[Dict],
    ml_data: List[Dict],
    output_path: str,
):
    """对比 Legacy vs ML 每次请求选择的 skill 数量分布"""
    legacy_counts = [len(item.get('selected_skills', [])) for item in legacy_data]
    ml_counts = [len(item.get('selected_skills', [])) for item in ml_data]

    fig, ax = plt.subplots(figsize=(10, 5))

    max_count = max(max(legacy_counts) if legacy_counts else 0,
                    max(ml_counts) if ml_counts else 0)
    if max_count == 0:
        max_count = 1
    bins = np.arange(0.5, max_count + 1.5, 1)

    ax.hist(legacy_counts, bins=bins, alpha=0.6, label='Legacy 关键词路由',
            color='#FF6B6B', edgecolor='black')
    ax.hist(ml_counts, bins=bins, alpha=0.6, label='ML SkillRouter',
            color='#4ECDC4', edgecolor='black')

    ax.set_xlabel('选择的 Skill 数量')
    ax.set_ylabel('样本数量')
    ax.set_title('Skill 选择数量分布对比')
    ax.legend()
    ax.set_xticks(range(1, max_count + 1))

    if legacy_counts:
        legacy_mean = np.mean(legacy_counts)
        ax.axvline(legacy_mean, color='#FF6B6B', linestyle='--', linewidth=2,
                  label=f'Legacy 均值: {legacy_mean:.1f}')
    if ml_counts:
        ml_mean = np.mean(ml_counts)
        ax.axvline(ml_mean, color='#4ECDC4', linestyle='--', linewidth=2,
                  label=f'ML 均值: {ml_mean:.1f}')

    ax.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  OK 图 4 已保存: {output_path}")


# ============================================
# 主函数
# ============================================

def main():
    parser = argparse.ArgumentParser(description="Skill Router 可视化对比报告")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="输出目录",
    )
    parser.add_argument(
        "--legacy-data",
        required=True,
        help="Legacy 系统数据路径",
    )
    parser.add_argument(
        "--ml-data",
        required=True,
        help="ML 系统数据路径",
    )
    parser.add_argument(
        "--training-stats",
        default="",
        help="训练统计路径（可选，用于训练曲线图）",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    setup_chinese_font()

    print("加载数据...")
    legacy_data = load_jsonl(args.legacy_data)
    ml_data = load_jsonl(args.ml_data)
    training_stats = load_training_stats(args.training_stats) if args.training_stats else None

    print(f"  Legacy 数据: {len(legacy_data)} 条")
    print(f"  ML 数据: {len(ml_data)} 条")
    print(f"  训练统计: {'有' if training_stats else '无'}")

    print("\n生成对比图表...")

    plot_accuracy_comparison(
        legacy_data,
        ml_data,
        str(output_dir / "1_accuracy_comparison.png"),
    )

    plot_token_waste_distribution(
        legacy_data,
        ml_data,
        str(output_dir / "2_token_waste_distribution.png"),
    )

    plot_training_curves(
        training_stats,
        str(output_dir / "3_training_curves.png"),
    )

    plot_skill_count_distribution(
        legacy_data,
        ml_data,
        str(output_dir / "4_skill_count_distribution.png"),
    )

    print(f"\n完成! 所有图表已保存到: {output_dir}")


if __name__ == "__main__":
    main()
