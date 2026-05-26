#!/usr/bin/env python3
"""
Skill Router Training — 一键运行流水线

串联：合成数据生成 → 真实数据收集 → LLM Judge 标注 → 训练集构建 → 模型训练 → 可视化报告

用法：
    # 使用 ZVAgent 适配器
    python scripts/run_pipeline.py --agent zvagent --agent-root ../ZVagent --phase all

    # 只运行合成数据生成
    python scripts/run_pipeline.py --agent zvagent --agent-root ../ZVagent --phase synthetic

    # 从已有的数据开始（跳过前面的步骤）
    python scripts/run_pipeline.py --phase train --training-data path/to/training_data.jsonl

环境变量：
    DEEPSEEK_API_KEY: DeepSeek API 密钥（Judge 和合成数据生成需要）
"""

import argparse
import os
import sys
from pathlib import Path

# 将包根目录加入 sys.path
PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))


def get_collector(args):
    """根据 --agent 参数创建对应的 DataCollector"""
    if args.agent == "zvagent":
        from adapters.zvagent import ZVAgentCollector
        if not args.agent_root:
            print("错误: 使用 --agent zvagent 时必须指定 --agent-root")
            sys.exit(1)
        return ZVAgentCollector(
            agent_root=args.agent_root,
            skills_dir=args.skills_dir,
        )
    elif args.agent == "custom":
        # 动态导入用户自定义适配器
        if not args.collector_module:
            print("错误: 使用 --agent custom 时必须指定 --collector-module")
            sys.exit(1)
        import importlib
        mod = importlib.import_module(args.collector_module)
        cls = getattr(mod, args.collector_class or "Collector")
        return cls(**(args.collector_kwargs or {}))
    else:
        print(f"错误: 未知的 agent 类型: {args.agent}")
        print("支持的类型: zvagent, custom")
        sys.exit(1)


def phase_synthetic(args, collector):
    """Phase A: 合成数据生成"""
    from core.utils import save_jsonl, load_jsonl

    print("\n" + "=" * 60)
    print("Phase A: 合成数据生成")
    print("=" * 60)

    output_path = args.synthetic_data
    if os.path.exists(output_path) and not args.force:
        existing = load_jsonl(output_path)
        print(f"  已存在 {len(existing)} 条合成数据，跳过（使用 --force 强制重新生成）")
        return

    # 获取 skill catalog
    skills_catalog = collector.get_skills_catalog()
    if not skills_catalog:
        print("错误: 无法获取 skill 目录，请检查适配器配置")
        return

    print(f"  Skill 目录: {skills_catalog.count(chr(10)) + 1} 个 skill")

    api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误: 未提供 API 密钥。请通过 --api-key 或 DEEPSEEK_API_KEY 环境变量设置。")
        return

    # 加载任务
    tasks_path = args.tasks_file
    if not tasks_path or not os.path.exists(tasks_path):
        print(f"错误: 任务文件不存在: {tasks_path}")
        print("请通过 --tasks-file 指定任务文件（每行一个任务描述）")
        return

    tasks = []
    with open(tasks_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                tasks.append(line)
    print(f"  任务数: {len(tasks)}")

    # 生成
    from core.utils import call_deepseek_api, sanitize_generated_item, parse_llm_json

    SIMULATION_PROMPT = """你是一个中文用户。根据任务描述，生成一个口语化的中文用户请求（20-100字）。

任务：{task_description}

可用 skills：
{skills_catalog}

输出格式（只输出JSON，不要有其他文字）：
{{"user_message": "口语化的中文请求", "ideal_skills": ["skill名称"], "reasoning": "为什么需要这些skill"}}

注意：
- user_message 必须是中文，口语化，20-100字
- ideal_skills 从上面的 skills 中选择（0-3个），很多问题不需要任何 skill（输出空数组 []）
- 直接输出JSON，不要有任何其他文字"""

    from tqdm import tqdm

    dataset = []
    num_variants = args.num_variants
    log_path = Path(output_path).with_suffix(".errors.log")
    if log_path.exists():
        log_path.write_text("", encoding="utf-8")

    print(f"\n  每个任务生成 {num_variants} 个变体，总请求数: {len(tasks) * num_variants}")

    for task in tqdm(tasks, desc="生成合成数据"):
        for variant_idx in range(num_variants):
            try:
                prompt = SIMULATION_PROMPT.format(
                    task_description=task,
                    skills_catalog=skills_catalog,
                )
                response = call_deepseek_api(
                    prompt=prompt,
                    api_key=api_key,
                    model=args.model,
                    api_base=args.api_base,
                    temperature=0.9,
                    max_tokens=1024,
                    log_path=log_path,
                )
                result = parse_llm_json(response)
                result = sanitize_generated_item(result)

                if "user_message" not in result:
                    continue

                dataset.append({
                    "user_message": result["user_message"],
                    "ideal_skills": result.get("ideal_skills", []),
                    "reasoning": result.get("reasoning", ""),
                    "source_task": task,
                    "variant_index": variant_idx,
                    "generation_method": "synthetic",
                })
            except Exception as e:
                from core.utils import log_error
                log_error(log_path, f"[Task failed] task={task!r} error={e}")

    save_jsonl(dataset, output_path)
    print(f"\n  合成数据生成完成: {len(dataset)} 条，保存到: {output_path}")


def phase_collect(args, collector):
    """Phase B: 真实数据收集"""
    print("\n" + "=" * 60)
    print("Phase B: 真实数据收集")
    print("=" * 60)

    output_path = args.real_data
    num_samples = args.collect_samples

    pairs = collector.collect_query_skills_pairs(num_samples=num_samples)
    print(f"  收集到 {len(pairs)} 条真实数据")

    from core.utils import save_jsonl
    save_jsonl(pairs, output_path)
    print(f"  保存到: {output_path}")


def phase_judge(args):
    """Phase C: LLM Judge 标注"""
    from core.judge import judge_dataset, load_reference_labels
    from core.utils import load_jsonl

    print("\n" + "=" * 60)
    print("Phase C: LLM Judge 标注")
    print("=" * 60)

    input_path = args.real_data
    if not os.path.exists(input_path):
        # 如果没有真实数据，用合成数据
        input_path = args.synthetic_data
        if not os.path.exists(input_path):
            print(f"错误: 输入文件不存在")
            return

    output_path = args.labeled_data
    api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误: 未提供 API 密钥")
        return

    data = load_jsonl(input_path)
    print(f"  加载数据: {len(data)} 条 ({input_path})")

    reference_labels = {}
    if os.path.exists(args.synthetic_data):
        reference_labels = load_reference_labels(args.synthetic_data)
        print(f"  参考标签: {len(reference_labels)} 条")

    judge_dataset(
        data=data,
        output_path=output_path,
        api_key=api_key,
        model=args.model,
        api_base=args.api_base,
        min_score=args.min_score,
        reference_labels=reference_labels if reference_labels else None,
        concurrency=args.concurrency,
    )


def phase_build(args):
    """Phase D: 训练集构建"""
    from core.dataset_builder import build_dataset

    print("\n" + "=" * 60)
    print("Phase D: 训练集构建")
    print("=" * 60)

    build_dataset(
        synthetic_path=args.synthetic_data,
        real_path=args.real_data if os.path.exists(args.real_data) else "",
        output_path=args.training_data,
        min_score=args.min_score,
        max_token_waste_ratio=args.max_waste_ratio,
    )


def phase_train(args):
    """Phase E: 模型训练"""
    from core.train import load_training_data, train_model, SkillRouter
    import random

    print("\n" + "=" * 60)
    print("Phase E: 模型训练")
    print("=" * 60)

    if not os.path.exists(args.training_data):
        print(f"错误: 训练数据不存在: {args.training_data}")
        return

    data, skill_index = load_training_data(args.training_data)
    print(f"  数据量: {len(data)} 条")
    print(f"  Skill 数量: {len(skill_index)}")

    random.seed(42)
    random.shuffle(data)
    split_idx = int(len(data) * (1 - args.val_split))
    train_data = data[:split_idx]
    val_data = data[split_idx:]
    print(f"  训练集: {len(train_data)}，验证集: {len(val_data)}")

    model = SkillRouter(num_skills=len(skill_index))

    train_model(
        model=model,
        train_data=train_data,
        val_data=val_data,
        output_dir=args.output_dir,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        device=args.device,
        skill_index=skill_index,
    )


def phase_visualize(args):
    """Phase F: 可视化报告"""
    from core.visualize import main as viz_main

    print("\n" + "=" * 60)
    print("Phase F: 可视化报告")
    print("=" * 60)

    sys.argv = [
        "visualize.py",
        "--output-dir", args.plots_dir,
        "--legacy-data", args.real_data if os.path.exists(args.real_data) else args.synthetic_data,
        "--ml-data", args.labeled_data if os.path.exists(args.labeled_data) else args.synthetic_data,
    ]
    if os.path.exists(args.training_stats):
        sys.argv.extend(["--training-stats", args.training_stats])

    viz_main()


def main():
    parser = argparse.ArgumentParser(
        description="Skill Router Training 一键流水线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Agent 选择
    parser.add_argument("--agent", choices=["zvagent", "custom"], default="zvagent",
                        help="Agent 类型（默认: zvagent）")
    parser.add_argument("--agent-root", default=None,
                        help="Agent 项目根目录")
    parser.add_argument("--skills-dir", default=None,
                        help="Skill 目录路径（可选，默认由适配器自动检测）")
    parser.add_argument("--collector-module", default=None,
                        help="自定义 Collector 模块路径（--agent custom 时使用）")
    parser.add_argument("--collector-class", default=None,
                        help="自定义 Collector 类名（默认: Collector）")

    # 流水线控制
    parser.add_argument("--phase", default="all",
                        choices=["synthetic", "collect", "judge", "build", "train", "visualize", "all"],
                        help="运行哪个阶段（默认: all）")

    # 数据路径
    parser.add_argument("--synthetic-data", default=str(PACKAGE_ROOT / "data" / "synthetic_data.jsonl"))
    parser.add_argument("--real-data", default=str(PACKAGE_ROOT / "data" / "real_data.jsonl"))
    parser.add_argument("--labeled-data", default=str(PACKAGE_ROOT / "data" / "labeled_data.jsonl"))
    parser.add_argument("--training-data", default=str(PACKAGE_ROOT / "data" / "training_data.jsonl"))
    parser.add_argument("--plots-dir", default=str(PACKAGE_ROOT / "data" / "plots"))
    parser.add_argument("--output-dir", default=str(PACKAGE_ROOT / "data" / "checkpoints"))
    parser.add_argument("--training-stats", default=str(PACKAGE_ROOT / "data" / "checkpoints" / "training_stats.json"))
    parser.add_argument("--tasks-file", default=None,
                        help="任务描述文件路径（每行一个，合成数据生成需要）")

    # API 配置
    parser.add_argument("--api-key", default=None, help="API 密钥")
    parser.add_argument("--model", default="deepseek-v4-pro", help="模型名称")
    parser.add_argument("--api-base", default="https://inferaichat.com/v1", help="API 基础 URL")

    # 训练参数
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--val-split", type=float, default=0.1)
    parser.add_argument("--device", default=None)

    # 数据生成参数
    parser.add_argument("--num-variants", type=int, default=5, help="每个任务的变体数")
    parser.add_argument("--collect-samples", type=int, default=100, help="收集的真实样本数")
    parser.add_argument("--concurrency", type=int, default=1, help="Judge 并发数")

    # 质量过滤
    parser.add_argument("--min-score", type=float, default=0.7)
    parser.add_argument("--max-waste-ratio", type=float, default=0.25)

    # 控制
    parser.add_argument("--force", action="store_true", help="强制重新执行已有数据的阶段")

    args = parser.parse_args()

    print("=" * 60)
    print("Skill Router Training Pipeline")
    print("=" * 60)
    print(f"  Agent: {args.agent}")
    print(f"  Phase: {args.phase}")
    print(f"  Data dir: {PACKAGE_ROOT / 'data'}")

    collector = None
    if args.agent in ("zvagent",) or args.agent == "custom":
        try:
            collector = get_collector(args)
            config = collector.get_config()
            print(f"  Agent 配置: {config}")
        except Exception as e:
            if args.phase in ("synthetic", "collect", "all"):
                print(f"警告: 适配器初始化失败 ({e})，部分阶段可能无法运行")

    phases = {
        "synthetic": lambda: phase_synthetic(args, collector),
        "collect": lambda: phase_collect(args, collector),
        "judge": lambda: phase_judge(args),
        "build": lambda: phase_build(args),
        "train": lambda: phase_train(args),
        "visualize": lambda: phase_visualize(args),
    }

    if args.phase == "all":
        for phase_name in ["synthetic", "collect", "judge", "build", "train", "visualize"]:
            try:
                phases[phase_name]()
            except Exception as e:
                print(f"\n  X 阶段 {phase_name} 失败: {e}")
                print(f"  继续下一阶段...")
    else:
        phases[args.phase]()

    print("\n" + "=" * 60)
    print("Pipeline 完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
