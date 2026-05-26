#!/usr/bin/env python3
"""
天磊虾 Skill Router 训练数据合成器（并行版）

基于 skill catalog + 种子查询，用 DeepSeek LLM 合成大量 (user_message, ideal_skills) 训练数据。
支持 ThreadPoolExecutor 并行调用 API 加速。

流程：
    1. 读取 skill_catalog.json（30 个 skill 的名称+描述+触发条件）
    2. 读取 seed_queries.jsonl（从日志提取的真实用户查询）
    3. 对每个种子查询，LLM 判断应该选择哪些 skills → 标注
    4. 对每个种子查询，LLM 生成变体（新的用户消息 + skill 选择）→ 扩充
    5. 额外：LLM 从零生成全新场景 → 进一步扩充
    6. 输出 synthetic_data.jsonl

用法：
    # 全量生成 1000+ 条（8 并发）
    python scripts/synthesize_tianleixia.py --api-key KEY --concurrency 8 --extra-queries 800

    # 试运行
    python scripts/synthesize_tianleixia.py --api-key KEY --dry-run

环境变量：
    DEEPSEEK_API_KEY: DeepSeek API 密钥
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

from tqdm import tqdm

# 将包根目录加入 sys.path
PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from core.utils import (
    call_deepseek_api,
    load_jsonl,
    log_error,
    parse_llm_json,
    parse_llm_json_array,
    repair_mojibake,
    save_jsonl,
    sanitize_generated_item,
)


# ============================================
# Prompt 模板
# ============================================

SYSTEM_PROMPT = """你是一个 Skill 路由标注专家。你的任务是分析用户的请求，判断应该调用哪些 skill 来完成任务。
必须严格输出 JSON，不要有任何其他文字。"""

LABEL_PROMPT = """请分析以下用户请求，判断应该调用哪些 skill 来完成任务。

## 用户请求
{user_message}

## 可用 Skills（共 {num_skills} 个）
{skills_catalog}

## 要求
从上面的可用 skills 中选择最相关的（0-{max_skills} 个）。
- 只选择真正需要的 skill，不要多选
- 很多简单问题不需要调用任何 skill（输出空数组 []）
- 某些任务可能需要组合多个 skill

输出格式（只输出 JSON）：
{{"user_message": "原始用户请求", "ideal_skills": ["skill-name-1", "skill-name-2"], "reasoning": "一句话说明为什么选择这些 skill"}}

现在请分析："""

VARIANT_PROMPT = """请基于以下用户请求和 skill 选择，生成 5 个变体。每个变体是一个新的用户请求（含义相似但表达不同），并标注对应的 skill 选择。

## 原始请求
{user_message}

## 原始 skill 选择
{ideal_skills}

## 可用 Skills（共 {num_skills} 个）
{skills_catalog}

## 变体要求
- 每个变体的 user_message 必须是中文，口语化或书面化均可，20-200字
- 变体应该保持与原始请求相似的意图，但用不同的表达方式
- 可以改变细节（如数据表名、字段名、具体需求），但大方向不变
- skill 选择应该根据变体的具体内容做相应调整
- 注意：很多请求不需要任何 skill，如果变体是简单的信息查询或闲聊，ideal_skills 应为空数组 []

输出格式（只输出 JSON 数组，不要输出任何其他文字）：
[{{"user_message":"变体1","ideal_skills":["skill-a"],"reasoning":"原因"}},{{"user_message":"变体2","ideal_skills":[],"reasoning":"简单查询"}}]

现在请生成 5 个变体："""

EXTRA_QUERY_PROMPT = """你是天磊虾智能助手的用户。天磊虾是一个类似 OpenClaw 的 AI 个人助手，具有以下能力：

## Skills 分类
{skills_summary}

## 你的任务
生成 {num_queries} 个真实用户可能会发送给天磊虾的请求。

要求：
- 请求类型要多样化：包括 OA 页面搭建、插件开发、工作流配置、需求分析、代码调试、测试、数据建模等
- 部分请求应该简单到不需要任何 skill（如直接问问题、闲聊、配置查询）
- 部分请求应该复杂到需要多个 skill 组合
- 用中文，口语化或书面化均可，20-200字
- 尽量覆盖不同的 skill 组合场景

输出格式（只输出 JSON 数组，不要输出任何其他文字）：
[{{"user_message":"请求1","ideal_skills":["skill-a"],"reasoning":"原因"}},{{"user_message":"请求2","ideal_skills":[],"reasoning":"简单查询"}}]

现在请生成 {num_queries} 个："""


def load_skill_catalog(path: str) -> List[Dict]:
    """加载 skill catalog JSON"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_skills_catalog(catalog: List[Dict]) -> str:
    """将 skill catalog 格式化为 prompt 文本"""
    lines = []
    for skill in catalog:
        lines.append(
            f"- {skill['skill_name']} ({skill['category']}): {skill['description']}\n"
            f"  触发条件: {skill['when_to_use']}"
        )
    return "\n\n".join(lines)


def format_skills_summary(catalog: List[Dict]) -> str:
    """将 skill catalog 格式化为简短摘要"""
    categories = {}
    for skill in catalog:
        cat = skill["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(skill["skill_name"])

    lines = []
    for cat, skills in categories.items():
        lines.append(f"- {cat} ({len(skills)}个): {', '.join(skills)}")
    return "\n".join(lines)


def label_seed_queries(
    seed_queries: List[Dict],
    catalog: List[Dict],
    api_key: str,
    model: str,
    api_base: str,
    max_skills: int = 3,
    concurrency: int = 1,
    log_path: Optional[Path] = None,
) -> List[Dict]:
    """对每个种子查询用 LLM 标注应该选择哪些 skills"""
    skills_text = format_skills_catalog(catalog)
    valid_names = {s["skill_name"] for s in catalog}

    def _label_one(item):
        user_message = item["user_message"]
        prompt = LABEL_PROMPT.format(
            user_message=user_message,
            num_skills=len(catalog),
            skills_catalog=skills_text,
            max_skills=max_skills,
        )
        try:
            response = call_deepseek_api(
                prompt=prompt,
                api_key=api_key,
                model=model,
                api_base=api_base,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=1000,
                log_path=log_path,
            )
            result = parse_llm_json(response)
            ideal_skills = [s for s in result.get("ideal_skills", []) if s in valid_names]
            return {
                "user_message": user_message,
                "ideal_skills": ideal_skills,
                "reasoning": result.get("reasoning", ""),
                "source": item.get("source", "seed"),
                "generation_method": "seed_labeled",
            }
        except Exception as e:
            log_error(log_path, f"[Label failed] {user_message[:50]}... {e}")
            return {
                "user_message": user_message,
                "ideal_skills": [],
                "reasoning": f"标注失败: {str(e)[:100]}",
                "source": item.get("source", "seed"),
                "generation_method": "seed_fallback",
            }

    if concurrency <= 1:
        return [_label_one(item) for item in tqdm(seed_queries, desc="标注种子查询")]

    labeled = [None] * len(seed_queries)
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(_label_one, item): i for i, item in enumerate(seed_queries)}
        for future in tqdm(as_completed(futures), total=len(futures), desc="标注种子查询"):
            idx = futures[future]
            try:
                labeled[idx] = future.result()
            except Exception as e:
                log_error(log_path, f"[Worker failed] idx={idx} {e}")
                labeled[idx] = {"user_message": seed_queries[idx]["user_message"], "ideal_skills": [], "reasoning": "", "source": "seed", "generation_method": "seed_fallback"}
    return labeled


def generate_variants(
    labeled_data: List[Dict],
    catalog: List[Dict],
    api_key: str,
    model: str,
    api_base: str,
    concurrency: int = 1,
    log_path: Optional[Path] = None,
) -> List[Dict]:
    """对每个已标注的种子查询生成变体"""
    skills_text = format_skills_catalog(catalog)
    valid_names = {s["skill_name"] for s in catalog}

    def _variant_one(item):
        user_message = item["user_message"]
        ideal_skills = ", ".join(item.get("ideal_skills", [])) or "无（不需要 skill）"
        prompt = VARIANT_PROMPT.format(
            user_message=user_message,
            ideal_skills=ideal_skills,
            num_skills=len(catalog),
            skills_catalog=skills_text,
        )
        for attempt in range(2):
            try:
                response = call_deepseek_api(
                    prompt=prompt, api_key=api_key, model=model, api_base=api_base,
                    system_prompt=SYSTEM_PROMPT, temperature=0.8, max_tokens=4000, log_path=log_path,
                )
                result = parse_llm_json_array(response)
                if not result:
                    raise ValueError("parse returned empty array")
                variants = []
                for variant in result:
                    if not isinstance(variant, dict) or "user_message" not in variant:
                        continue
                    vs = [s for s in variant.get("ideal_skills", []) if s in valid_names]
                    variants.append({
                        "user_message": variant["user_message"],
                        "ideal_skills": vs,
                        "reasoning": variant.get("reasoning", ""),
                        "source": item.get("source", "seed"),
                        "generation_method": "variant",
                        "parent_message": user_message,
                    })
                return variants
            except Exception as e:
                if attempt == 0:
                    time.sleep(1)
                    continue
                log_error(log_path, f"[Variant failed] {user_message[:50]}... {e}")
                return []

    if concurrency <= 1:
        all_variants = []
        for item in tqdm(labeled_data, desc="生成变体"):
            all_variants.extend(_variant_one(item))
        return all_variants

    all_variants = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(_variant_one, item): item for item in labeled_data}
        for future in tqdm(as_completed(futures), total=len(futures), desc="生成变体"):
            try:
                all_variants.extend(future.result())
            except Exception as e:
                log_error(log_path, f"[Variant worker failed] {e}")
    return all_variants


def generate_extra_queries(
    catalog: List[Dict],
    api_key: str,
    model: str,
    api_base: str,
    num_queries: int = 50,
    batch_size: int = 10,
    concurrency: int = 1,
    log_path: Optional[Path] = None,
) -> List[Dict]:
    """从零生成全新的用户请求 + skill 选择"""
    skills_summary = format_skills_summary(catalog)
    valid_names = {s["skill_name"] for s in catalog}
    num_batches = (num_queries + batch_size - 1) // batch_size

    def _batch_one(batch_idx):
        current_batch_size = min(batch_size, num_queries - batch_idx * batch_size)
        if current_batch_size <= 0:
            return []
        prompt = EXTRA_QUERY_PROMPT.format(skills_summary=skills_summary, num_queries=current_batch_size)
        for attempt in range(2):
            try:
                response = call_deepseek_api(
                    prompt=prompt, api_key=api_key, model=model, api_base=api_base,
                    system_prompt=SYSTEM_PROMPT, temperature=0.9, max_tokens=4000, log_path=log_path,
                )
                result = parse_llm_json_array(response)
                if not result:
                    raise ValueError("parse returned empty array")
                queries = []
                for item in result:
                    if not isinstance(item, dict) or "user_message" not in item:
                        continue
                    skills = [s for s in item.get("ideal_skills", []) if s in valid_names]
                    queries.append({
                        "user_message": item["user_message"],
                        "ideal_skills": skills,
                        "reasoning": item.get("reasoning", ""),
                        "source": "synthetic",
                        "generation_method": "extra",
                    })
                return queries
            except Exception as e:
                if attempt == 0:
                    time.sleep(1)
                    continue
                log_error(log_path, f"[Extra batch {batch_idx} failed] {e}")
                return []

    if concurrency <= 1:
        all_queries = []
        for batch_idx in tqdm(range(num_batches), desc="生成全新场景"):
            all_queries.extend(_batch_one(batch_idx))
        return all_queries

    all_queries = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(_batch_one, i): i for i in range(num_batches)}
        for future in tqdm(as_completed(futures), total=len(futures), desc="生成全新场景"):
            try:
                all_queries.extend(future.result())
            except Exception as e:
                log_error(log_path, f"[Extra worker failed] {e}")
    return all_queries


def deduplicate(data: List[Dict]) -> List[Dict]:
    """去重：基于 user_message 去重，保留第一个出现的"""
    seen = set()
    deduped = []
    for item in data:
        key = item["user_message"].strip()
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def main():
    parser = argparse.ArgumentParser(description="天磊虾 Skill Router 训练数据合成器")
    parser.add_argument(
        "--api-key",
        default=None,
        help="DeepSeek API 密钥（也可通过 DEEPSEEK_API_KEY 环境变量设置）",
    )
    parser.add_argument(
        "--model",
        default="deepseek-v4-pro",
        help="模型名称（默认: deepseek-v4-pro）",
    )
    parser.add_argument(
        "--api-base",
        default="https://inferaichat.com/v1",
        help="API 基础 URL",
    )
    parser.add_argument(
        "--skill-catalog",
        default=str(PACKAGE_ROOT / "data" / "skill_catalog.json"),
        help="Skill catalog 文件路径",
    )
    parser.add_argument(
        "--seed-queries",
        default=str(PACKAGE_ROOT / "data" / "seed_queries.jsonl"),
        help="种子查询文件路径",
    )
    parser.add_argument(
        "--output",
        default=str(PACKAGE_ROOT / "data" / "synthetic_data.jsonl"),
        help="输出文件路径",
    )
    parser.add_argument(
        "--variants-per-seed",
        type=int,
        default=5,
        help="每个种子查询生成的变体数（默认: 5）",
    )
    # 每个种子生成 5 个变体，23 种子 × 5 = 115 条
    # Phase 3 每批 5 条，降低截断率
    parser.add_argument(
        "--extra-queries",
        type=int,
        default=1000,
        help="额外从零生成的查询数（默认: 1000）",
    )
    parser.add_argument(
        "--extra-batch-size",
        type=int,
        default=5,
        help="Phase 3 每批生成数量（默认: 5，降低截断率）",
    )
    parser.add_argument(
        "--max-skills",
        type=int,
        default=3,
        help="每个查询最多选择的 skill 数（默认: 3）",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=8,
        help="并发 API 调用数（默认: 8）",
    )
    parser.add_argument(
        "--phase",
        default="all",
        choices=["label", "variants", "extra", "all"],
        help="运行哪个阶段",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式：只处理 2 条种子查询",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新生成（覆盖已有文件）",
    )

    args = parser.parse_args()

    # 检查 API key
    api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误: 未提供 API 密钥。请通过 --api-key 或 DEEPSEEK_API_KEY 环境变量设置。")
        return

    # 加载 skill catalog
    print(f"加载 skill catalog: {args.skill_catalog}")
    catalog = load_skill_catalog(args.skill_catalog)
    print(f"  共 {len(catalog)} 个 skill")

    # 加载种子查询
    print(f"加载种子查询: {args.seed_queries}")
    seed_queries = load_jsonl(args.seed_queries)
    print(f"  共 {len(seed_queries)} 条种子查询")

    if args.dry_run:
        seed_queries = seed_queries[:2]
        print(f"  试运行模式：只处理 {len(seed_queries)} 条")

    # 准备日志
    output_path = Path(args.output)
    log_path = output_path.with_suffix(".errors.log")
    if log_path.exists():
        log_path.write_text("", encoding="utf-8")

    all_data = []

    # Phase 1: 标注种子查询
    if args.phase in ("label", "all"):
        print(f"\n{'='*60}")
        print("Phase 1: 标注种子查询")
        print(f"{'='*60}")
        labeled = label_seed_queries(
            seed_queries=seed_queries,
            catalog=catalog,
            api_key=api_key,
            model=args.model,
            api_base=args.api_base,
            max_skills=args.max_skills,
            concurrency=args.concurrency,
            log_path=log_path,
        )
        all_data.extend(labeled)
        print(f"  标注完成: {len(labeled)} 条")

        # 统计
        has_skills = sum(1 for item in labeled if item["ideal_skills"])
        print(f"  有 skill 选择: {has_skills} 条")
        print(f"  无 skill 选择: {len(labeled) - has_skills} 条")

    # Phase 2: 生成变体
    if args.phase in ("variants", "all"):
        print(f"\n{'='*60}")
        print("Phase 2: 生成变体")
        print(f"{'='*60}")

        # 如果 phase 是 variants，需要先加载已标注的数据
        if args.phase == "variants":
            # 尝试从已有输出加载
            existing = load_jsonl(args.output)
            labeled = [d for d in existing if d.get("generation_method") == "seed_labeled"]
            if not labeled:
                print("  错误: 没有已标注的种子数据，请先运行 label 阶段")
                return
        else:
            labeled = all_data

        variants = generate_variants(
            labeled_data=labeled,
            catalog=catalog,
            api_key=api_key,
            model=args.model,
            api_base=args.api_base,
            concurrency=args.concurrency,
            log_path=log_path,
        )
        all_data.extend(variants)
        print(f"  变体生成完成: {len(variants)} 条")

    # Phase 3: 生成全新场景
    if args.phase in ("extra", "all"):
        print(f"\n{'='*60}")
        print("Phase 3: 生成全新场景")
        print(f"{'='*60}")
        extra = generate_extra_queries(
            catalog=catalog,
            api_key=api_key,
            model=args.model,
            api_base=args.api_base,
            num_queries=args.extra_queries,
            batch_size=args.extra_batch_size,
            concurrency=args.concurrency,
            log_path=log_path,
        )
        all_data.extend(extra)
        print(f"  全新场景生成完成: {len(extra)} 条")

    # 如果只运行单个 phase，需要从文件合并
    if args.phase != "all":
        existing = load_jsonl(args.output)
        all_data = existing + all_data

    # 去重
    all_data = deduplicate(all_data)
    print(f"\n去重后总计: {len(all_data)} 条")

    # 保存
    save_jsonl(all_data, args.output)
    print(f"保存到: {args.output}")

    # 统计
    print(f"\n生成方式分布:")
    methods = {}
    for item in all_data:
        method = item.get("generation_method", "unknown")
        methods[method] = methods.get(method, 0) + 1
    for method, count in sorted(methods.items()):
        print(f"  {method}: {count}")

    has_skills = sum(1 for item in all_data if item.get("ideal_skills"))
    print(f"\n有 skill 选择: {has_skills} / {len(all_data)} ({has_skills/len(all_data)*100:.1f}%)")

    print(f"\n合成完成!")


if __name__ == "__main__":
    main()
