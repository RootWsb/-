#!/usr/bin/env python3
"""
Skill Quality Judge - LLM Judge 标注 skill 选择质量

用 DeepSeek V4 Pro 评估 skill 选择的准确性，生成带分数的训练数据。

用法：
    python core/judge.py --input real_data.jsonl --output labeled_data.jsonl

环境变量：
    DEEPSEEK_API_KEY: DeepSeek API 密钥

依赖：
    pip install requests tqdm
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

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from core.utils import (
    call_deepseek_api,
    log_error,
    load_jsonl,
    parse_llm_json,
    repair_mojibake,
    save_jsonl,
)

# ============================================
# 配置
# ============================================

DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_API_BASE = "https://inferaichat.com/v1"
MAX_CONSECUTIVE_FAILURES = 8

JSON_ONLY_SYSTEM_PROMPT = """你是一个严格的 JSON 标注器。你的全部输出必须是一个 JSON 对象。
禁止输出分析过程、解释、Markdown、代码块或任何 JSON 外的文字。
第一个字符必须是 {，最后一个字符必须是 }。"""

JUDGE_PROMPT = """请评估以下 skill 选择的质量，并只输出 JSON。

用户请求：
{user_message}

可用 skills（共 {num_skills} 个）：
{available_skills}

当前选择：
{selected_skills}

字段要求：
- correct_skills: 理想情况下应该选择哪些 skill（从可用 skills 中选）
- missed_skills: 漏选了哪些重要的 skill
- unnecessary_skills: 多选了哪些不必要的 skill
- selection_score: 选择准确度评分（0.0-1.0，1.0 表示完美选择）
- token_waste_ratio: token 浪费比例（0.0-1.0，越低越好，表示多选了不必要的 skill）
- reasoning: 一句话说明评估理由，最多 40 个汉字

严格输出这个 JSON 结构，不要先解释：
{{
  "correct_skills": ["skill-a", "skill-b"],
  "missed_skills": ["skill-c"],
  "unnecessary_skills": ["skill-d"],
  "selection_score": 0.85,
  "token_waste_ratio": 0.15,
  "reasoning": "选择了主要相关的 skill，但漏掉了 skill-c"
}}

现在请评估："""

REPAIR_PROMPT = """下面是一段没有按要求输出 JSON 的 skill 评估结果。请基于用户请求、可用 skills、当前选择和这段文本，补全为严格 JSON。

用户请求：
{user_message}

可用 skills：
{available_skills}

当前选择：
{selected_skills}

原始输出：
{raw_response}

只输出 JSON，字段为 correct_skills, missed_skills, unnecessary_skills, selection_score, token_waste_ratio, reasoning。"""


# ============================================
# 评估逻辑
# ============================================

def normalize_judgment(judgment: Dict) -> Dict:
    """规范化 Judge 输出字段，避免类型不一致影响后续流程。"""
    judgment = dict(judgment)
    for key in ("correct_skills", "missed_skills", "unnecessary_skills"):
        value = judgment.get(key, [])
        if not isinstance(value, list):
            value = []
        judgment[key] = [str(skill).strip() for skill in value if str(skill).strip()]

    for key, default in (("selection_score", 0.0), ("token_waste_ratio", 0.5)):
        try:
            value = float(judgment.get(key, default))
        except (TypeError, ValueError):
            value = default
        judgment[key] = max(0.0, min(1.0, value))

    # 兼容旧字段名 token_efficiency
    if "token_efficiency" in judgment and "token_waste_ratio" not in judgment:
        judgment["token_waste_ratio"] = judgment.pop("token_efficiency")
    elif "token_efficiency" in judgment:
        judgment.pop("token_efficiency", None)

    if isinstance(judgment.get("reasoning"), str):
        judgment["reasoning"] = repair_mojibake(judgment["reasoning"]).strip()
    else:
        judgment["reasoning"] = ""

    return judgment


def load_reference_labels(reference_path: Optional[str]) -> Dict[str, List[str]]:
    """从 synthetic_data.jsonl 读取 user_message -> ideal_skills 参考标签。"""
    if not reference_path:
        return {}
    data = load_jsonl(reference_path)
    labels = {}
    for item in data:
        user_message = item.get("user_message", "")
        ideal_skills = item.get("ideal_skills", [])
        if user_message and isinstance(ideal_skills, list):
            labels[user_message] = [str(skill).strip() for skill in ideal_skills if str(skill).strip()]
    return labels


def build_reference_judgment(sample: Dict, ideal_skills: List[str]) -> Dict:
    """用已有 ideal_skills 生成和 LLM Judge 相同格式的评分结果。"""
    selected_skills = sample.get("selected_skills", [])
    selected_set = set(selected_skills)
    ideal_set = set(ideal_skills)

    missed = sorted(ideal_set - selected_set)
    unnecessary = sorted(selected_set - ideal_set)

    if ideal_set:
        precision = len(selected_set & ideal_set) / max(1, len(selected_set))
        recall = len(selected_set & ideal_set) / len(ideal_set)
        if precision + recall:
            selection_score = 2 * precision * recall / (precision + recall)
        else:
            selection_score = 0.0
    else:
        selection_score = 1.0 if not selected_set else max(0.0, 1.0 - 0.2 * len(selected_set))

    token_waste_ratio = len(unnecessary) / max(1, len(selected_skills))

    judgment = {
        "correct_skills": sorted(ideal_set),
        "missed_skills": missed,
        "unnecessary_skills": unnecessary,
        "selection_score": round(selection_score, 3),
        "token_waste_ratio": round(token_waste_ratio, 3),
        "reasoning": "基于合成数据的 ideal_skills 自动评分",
    }
    return normalize_judgment(judgment)


def parse_judge_response(response: str) -> Dict:
    """解析 LLM Judge 返回的 JSON，处理各种格式问题。"""
    if not response or not response.strip():
        raise ValueError("LLM 返回空响应")

    response = repair_mojibake(response.strip())
    if response.startswith("```"):
        lines = response.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        response = "\n".join(lines).strip()

    try:
        return normalize_judgment(json.loads(response))
    except json.JSONDecodeError:
        pass

    # 提取 JSON 块
    start = response.find("{")
    end = response.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return normalize_judgment(json.loads(response[start : end + 1]))
        except json.JSONDecodeError:
            pass

    import re
    match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
    if match:
        try:
            return normalize_judgment(json.loads(match.group()))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法解析 LLM 响应: {response[:1000]}")


def repair_judgment_response(
    raw_response: str,
    sample: Dict,
    api_key: str,
    model: str,
    api_base: str,
    log_path: Optional[Path] = None,
) -> Dict:
    """让模型把非 JSON 输出修复为 JSON。"""
    repair_prompt = REPAIR_PROMPT.format(
        user_message=sample.get("user_message", ""),
        available_skills="\n".join([f"- {s}" for s in sample.get("available_skills", [])]),
        selected_skills=", ".join(sample.get("selected_skills", [])) or "无",
        raw_response=repair_mojibake(raw_response)[:3000],
    )
    repaired = call_deepseek_api(
        prompt=repair_prompt,
        api_key=api_key,
        model=model,
        api_base=api_base,
        system_prompt=JSON_ONLY_SYSTEM_PROMPT,
        temperature=0.0,
        max_tokens=900,
        log_path=log_path,
    )
    return parse_judge_response(repaired)


def judge_single_sample(
    sample: Dict,
    api_key: str,
    model: str,
    api_base: str,
    log_path: Optional[Path] = None,
    reference_labels: Optional[Dict[str, List[str]]] = None,
    prefer_reference_labels: bool = False,
) -> Optional[Dict]:
    """
    评估单个样本的 skill 选择质量。

    Returns:
        带评分的样本，失败返回 None
    """
    user_message = sample.get("user_message", "")
    selected_skills = sample.get("selected_skills", [])
    available_skills = sample.get("available_skills", [])
    reference_ideal = None
    if reference_labels:
        reference_ideal = reference_labels.get(user_message)
    if reference_ideal is None and isinstance(sample.get("ideal_skills"), list):
        reference_ideal = sample.get("ideal_skills")

    if prefer_reference_labels and reference_ideal is not None:
        judgment = build_reference_judgment(sample, reference_ideal)
        return {
            **sample,
            "judge": judgment,
            "selection_score": judgment.get("selection_score", 0.0),
            "token_waste_ratio": judgment.get("token_waste_ratio", 0.5),
            "ideal_skills": judgment.get("correct_skills", []),
            "judge_source": "reference_labels",
        }

    prompt = JUDGE_PROMPT.format(
        user_message=user_message,
        num_skills=len(available_skills),
        available_skills="\n".join([f"- {s}" for s in available_skills]),
        selected_skills=", ".join(selected_skills) if selected_skills else "无",
    )

    try:
        response = call_deepseek_api(
            prompt=prompt,
            api_key=api_key,
            model=model,
            api_base=api_base,
            system_prompt=JSON_ONLY_SYSTEM_PROMPT,
            log_path=log_path,
        )
        try:
            judgment = parse_judge_response(response)
        except ValueError as parse_err:
            log_error(
                log_path,
                f"[Parse failed, trying repair] {type(parse_err).__name__}: {str(parse_err)}",
            )
            judgment = repair_judgment_response(
                raw_response=response,
                sample=sample,
                api_key=api_key,
                model=model,
                api_base=api_base,
                log_path=log_path,
            )

        if "selection_score" not in judgment:
            raise ValueError(f"缺少 selection_score: {judgment}")

        result = {
            **sample,
            "judge": judgment,
            "selection_score": judgment.get("selection_score", 0.0),
            "token_waste_ratio": judgment.get("token_waste_ratio", 0.5),
            "ideal_skills": judgment.get("correct_skills", []),
            "judge_source": "llm",
        }

        return result

    except Exception as e:
        if reference_ideal is not None:
            judgment = build_reference_judgment(sample, reference_ideal)
            log_error(
                log_path,
                f"[Judge fallback to reference] user_message={user_message!r} "
                f"error={type(e).__name__}: {str(e)}",
            )
            return {
                **sample,
                "judge": judgment,
                "selection_score": judgment.get("selection_score", 0.0),
                "token_waste_ratio": judgment.get("token_waste_ratio", 0.5),
                "ideal_skills": judgment.get("correct_skills", []),
                "judge_source": "reference_fallback",
            }
        log_error(
            log_path,
            f"[Judge failed] user_message={user_message!r} "
            f"selected_skills={selected_skills!r} error={type(e).__name__}: {str(e)}",
        )
        print(f"  X 评估失败: {user_message[:50]}... - {e}")
        return None


def judge_dataset(
    data: List[Dict],
    output_path: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    api_base: str = DEFAULT_API_BASE,
    min_score: float = 0.7,
    max_consecutive_failures: int = MAX_CONSECUTIVE_FAILURES,
    reference_labels: Optional[Dict[str, List[str]]] = None,
    prefer_reference_labels: bool = False,
    concurrency: int = 1,
):
    """
    批量评估训练数据。

    Args:
        data: 输入数据列表
        output_path: 输出文件路径
        api_key: API 密钥
        model: 模型名称
        api_base: API 基础 URL
        min_score: 最低分数阈值
    """
    print(f"\n开始评估 skill 选择质量...")
    print(f"  输入数据量: {len(data)}")
    print(f"  模型: {model}")
    print(f"  最低分数阈值: {min_score}")
    print(f"  并发数: {concurrency}")
    if reference_labels:
        mode = "优先使用" if prefer_reference_labels else "失败时兜底使用"
        print(f"  参考标签: {len(reference_labels)} 条（{mode}）")

    output_file = Path(output_path) if output_path else None
    log_path = output_file.with_suffix(".errors.log") if output_file else Path("_judge_errors.log")
    if log_path.exists():
        log_path.write_text("", encoding="utf-8")
    print(f"  错误日志: {log_path}")
    print()

    results: List[Optional[Dict]] = [None] * len(data)
    success_count = 0
    error_count = 0
    consecutive_failures = 0

    concurrency = max(1, int(concurrency or 1))

    def run_one(index: int, item: Dict):
        return index, judge_single_sample(
            sample=item,
            api_key=api_key,
            model=model,
            api_base=api_base,
            log_path=log_path,
            reference_labels=reference_labels,
            prefer_reference_labels=prefer_reference_labels,
        )

    if concurrency == 1:
        iterator = tqdm(enumerate(data), total=len(data), desc="评估样本")
        for index, item in iterator:
            _, result = run_one(index, item)
            results[index] = result
            if result:
                success_count += 1
                consecutive_failures = 0
                time.sleep(0.1)
            else:
                error_count += 1
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    raise RuntimeError(
                        f"连续评估失败 {consecutive_failures} 次，已停止。"
                        f"请查看错误日志: {log_path}"
                    )
                time.sleep(1)
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {
                executor.submit(run_one, index, item): index
                for index, item in enumerate(data)
            }
            for future in tqdm(as_completed(futures), total=len(futures), desc="评估样本"):
                index = futures[future]
                try:
                    result_index, result = future.result()
                except Exception as e:
                    result_index, result = index, None
                    log_error(
                        log_path,
                        f"[Worker failed] index={index} error={type(e).__name__}: {str(e)}",
                    )
                results[result_index] = result
                if result:
                    success_count += 1
                else:
                    error_count += 1

    labeled_data = [item for item in results if item]
    filtered_data = [item for item in labeled_data if item.get("selection_score", 0) >= min_score]

    if output_path:
        save_jsonl(filtered_data, output_path)

    scores = [item.get("selection_score", 0) for item in labeled_data]

    print(f"\n评估完成!")
    print(f"  成功评估: {success_count}")
    print(f"  评估失败: {error_count}")
    print(f"  保留样本（score >= {min_score}）: {len(filtered_data)}")
    if output_path:
        print(f"  保存到: {output_file}")
    if error_count:
        print(f"  错误日志: {log_path}")

    if scores:
        print(f"\n评分统计:")
        print(f"  平均分: {sum(scores) / len(scores):.3f}")
        print(f"  最高分: {max(scores):.3f}")
        print(f"  最低分: {min(scores):.3f}")

    return filtered_data


def main():
    parser = argparse.ArgumentParser(description="LLM Judge 标注 skill 选择质量")
    parser.add_argument(
        "--input",
        required=True,
        help="输入文件路径（real_data.jsonl 或 synthetic_data.jsonl）",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="输出文件路径",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"模型名称 (默认: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=f"API 基础 URL (默认: {DEFAULT_API_BASE})",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API 密钥 (也可通过 DEEPSEEK_API_KEY 环境变量设置)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.7,
        help="最低分数阈值（默认: 0.7）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式，只评估 1 条数据",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="最多评估多少条数据（默认: 全部）",
    )
    parser.add_argument(
        "--reference",
        default="",
        help="参考标签文件路径（用于 API 失败兜底）",
    )
    parser.add_argument(
        "--prefer-reference-labels",
        action="store_true",
        help="优先使用 reference 中的 ideal_skills 生成标签，不调用 LLM Judge",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="并发评估请求数（默认: 1）",
    )

    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误: 未提供 API 密钥。请通过 --api-key 或 DEEPSEEK_API_KEY 环境变量设置。")
        return

    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}")
        return

    print(f"加载输入文件: {args.input}")
    data = load_jsonl(args.input)
    print(f"  加载了 {len(data)} 条数据")

    reference_labels = load_reference_labels(args.reference) if args.reference else {}
    if reference_labels:
        print(f"  加载参考标签: {len(reference_labels)} 条 ({args.reference})")

    if args.dry_run:
        data = data[:1]
        print("\n试运行模式：只评估 1 条数据")
    elif args.max_samples is not None:
        data = data[:max(0, args.max_samples)]
        print(f"\n小批量模式：只评估 {len(data)} 条数据")

    judge_dataset(
        data=data,
        output_path=args.output,
        api_key=api_key,
        model=args.model,
        api_base=args.api_base,
        min_score=args.min_score,
        reference_labels=reference_labels,
        prefer_reference_labels=args.prefer_reference_labels,
        concurrency=args.concurrency,
    )

    if os.path.exists(args.output):
        print(f"\n评估示例:")
        with open(args.output, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 3:
                    break
                item = json.loads(line)
                print(f"\n  [{i+1}] 用户请求: {item['user_message']}")
                print(f"      选择的 skills: {item.get('selected_skills', [])}")
                print(f"      理想 skills: {item.get('ideal_skills', [])}")
                print(f"      评分: {item.get('selection_score', 0):.3f}")
                print(f"      标注来源: {item.get('judge_source', 'unknown')}")


if __name__ == "__main__":
    main()
