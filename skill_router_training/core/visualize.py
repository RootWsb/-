#!/usr/bin/env python3
"""Generate comparison plots for Legacy routing vs ML SkillRouter."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from core.utils import load_jsonl


def setup_plot_style():
    """Use fonts that are normally available in headless Linux environments."""
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Liberation Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def load_training_stats(path: str) -> Optional[Dict]:
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def mean(values: List[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def plot_accuracy_comparison(legacy_data: List[Dict], ml_data: List[Dict], output_path: str):
    legacy_avg = mean([item.get("selection_score", 0.0) for item in legacy_data])
    ml_avg = mean([item.get("selection_score", 0.0) for item in ml_data])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    x = np.arange(1)
    width = 0.35

    bars1 = ax1.bar(x - width / 2, [legacy_avg * 100], width, label="Legacy", color="#FF6B6B")
    bars2 = ax1.bar(x + width / 2, [ml_avg * 100], width, label="ML SkillRouter", color="#4ECDC4")

    ax1.set_ylabel("Selection Score (%)")
    ax1.set_title("Skill Selection Score")
    ax1.set_xticks(x)
    ax1.set_xticklabels(["Average"])
    ax1.legend()
    ax1.set_ylim(0, 100)

    for bars in (bars1, bars2):
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2, height, f"{height:.1f}%", ha="center", va="bottom")

    bars3 = ax2.bar(x - width / 2, [len(legacy_data)], width, label="Legacy", color="#FF6B6B")
    bars4 = ax2.bar(x + width / 2, [len(ml_data)], width, label="ML SkillRouter", color="#4ECDC4")

    ax2.set_ylabel("Sample Count")
    ax2.set_title("Evaluation Samples")
    ax2.set_xticks(x)
    ax2.set_xticklabels(["Dataset"])
    ax2.legend()

    for bars in (bars3, bars4):
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width() / 2, height, f"{int(height)}", ha="center", va="bottom")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  OK saved: {output_path}")


def plot_token_waste_distribution(legacy_data: List[Dict], ml_data: List[Dict], output_path: str):
    legacy_waste = [item.get("token_waste_ratio", 0.0) for item in legacy_data]
    ml_waste = [item.get("token_waste_ratio", 0.0) for item in ml_data]

    fig, ax = plt.subplots(figsize=(8, 5))
    bp = ax.boxplot([legacy_waste, ml_waste], tick_labels=["Legacy", "ML SkillRouter"], patch_artist=True)

    bp["boxes"][0].set_facecolor("#FF6B6B")
    bp["boxes"][1].set_facecolor("#4ECDC4")

    ax.set_ylabel("Token Waste Ratio")
    ax.set_title("Token Waste Distribution (lower is better)")
    ax.set_ylim(0, 1)

    for i, data in enumerate([legacy_waste, ml_waste]):
        if data:
            avg = mean(data)
            ax.text(i + 1, min(avg + 0.05, 0.98), f"mean: {avg:.2f}", ha="center", fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  OK saved: {output_path}")


def plot_training_curves(training_stats: Optional[Dict], output_path: str):
    if not training_stats:
        print("  SKIP training curves: no training stats file")
        return

    history = training_stats.get("history") or []
    if history:
        epochs = [item.get("epoch", i + 1) for i, item in enumerate(history)]
        train_losses = [item.get("train_loss", np.nan) for item in history]
        val_losses = [item.get("val_loss", np.nan) for item in history]
        train_accs = [item.get("train_accuracy", np.nan) for item in history]
        val_accs = [item.get("val_accuracy", np.nan) for item in history]
        loss_title = "Training Loss"
        acc_title = "Training Accuracy"
    else:
        epoch = training_stats.get("num_epochs", 1)
        epochs = [epoch]
        train_losses = [training_stats.get("final_train_loss", np.nan)]
        val_losses = [training_stats.get("best_val_loss", np.nan)]
        train_accs = [training_stats.get("final_train_accuracy", np.nan)]
        final_val_metrics = training_stats.get("final_val_metrics") or {}
        val_accs = [final_val_metrics.get("element_accuracy", np.nan)]
        loss_title = "Training Loss Summary"
        acc_title = "Training Accuracy Summary"

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    ax1.plot(epochs, train_losses, "b-o", label="Train Loss", markersize=4)
    ax1.plot(epochs, val_losses, "r-s", label="Validation Loss", markersize=4)
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("BCE Loss")
    ax1.set_title(loss_title)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.plot(epochs, train_accs, "b-o", label="Train Accuracy", markersize=4)
    ax2.plot(epochs, val_accs, "r-s", label="Validation Accuracy", markersize=4)
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("Accuracy")
    ax2.set_title(acc_title)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  OK saved: {output_path}")


def plot_skill_count_distribution(legacy_data: List[Dict], ml_data: List[Dict], output_path: str):
    legacy_counts = [len(item.get("selected_skills", [])) for item in legacy_data]
    ml_counts = [len(item.get("selected_skills", [])) for item in ml_data]

    fig, ax = plt.subplots(figsize=(10, 5))

    max_count = max(max(legacy_counts) if legacy_counts else 0, max(ml_counts) if ml_counts else 0)
    max_count = max(max_count, 1)
    bins = np.arange(-0.5, max_count + 1.5, 1)

    ax.hist(legacy_counts, bins=bins, alpha=0.6, label="Legacy", color="#FF6B6B", edgecolor="black")
    ax.hist(ml_counts, bins=bins, alpha=0.6, label="ML SkillRouter", color="#4ECDC4", edgecolor="black")

    ax.set_xlabel("Selected Skill Count")
    ax.set_ylabel("Sample Count")
    ax.set_title("Selected Skill Count Distribution")
    ax.set_xticks(range(0, max_count + 1))

    if legacy_counts:
        legacy_mean = mean(legacy_counts)
        ax.axvline(legacy_mean, color="#FF6B6B", linestyle="--", linewidth=2, label=f"Legacy mean: {legacy_mean:.1f}")
    if ml_counts:
        ml_mean = mean(ml_counts)
        ax.axvline(ml_mean, color="#4ECDC4", linestyle="--", linewidth=2, label=f"ML mean: {ml_mean:.1f}")

    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  OK saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Skill Router comparison plots.")
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument("--legacy-data", required=True, help="Legacy result JSONL.")
    parser.add_argument("--ml-data", required=True, help="ML result JSONL.")
    parser.add_argument("--training-stats", default="", help="Optional training_stats.json path.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    setup_plot_style()

    print("Loading data...")
    legacy_data = load_jsonl(args.legacy_data)
    ml_data = load_jsonl(args.ml_data)
    training_stats = load_training_stats(args.training_stats) if args.training_stats else None

    print(f"  Legacy rows: {len(legacy_data)}")
    print(f"  ML rows: {len(ml_data)}")
    print(f"  Training stats: {'yes' if training_stats else 'no'}")

    print("\nGenerating plots...")
    plot_accuracy_comparison(legacy_data, ml_data, str(output_dir / "1_accuracy_comparison.png"))
    plot_token_waste_distribution(legacy_data, ml_data, str(output_dir / "2_token_waste_distribution.png"))
    plot_training_curves(training_stats, str(output_dir / "3_training_curves.png"))
    plot_skill_count_distribution(legacy_data, ml_data, str(output_dir / "4_skill_count_distribution.png"))

    print(f"\nDone. Plots saved to: {output_dir}")


if __name__ == "__main__":
    main()
