#!/usr/bin/env python3
"""Build hard-case synthetic-data prompts from router evaluation failures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def save_jsonl(rows: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def skill_set(row: Dict[str, Any], key: str) -> Set[str]:
    return set(row.get(key) or [])


def row_error(row: Dict[str, Any]) -> Dict[str, List[str]]:
    selected = skill_set(row, "selected_skills")
    ideal = skill_set(row, "ideal_skills")
    return {
        "missing": sorted(ideal - selected),
        "extra": sorted(selected - ideal),
    }


def rank_hard_cases(rows: List[Dict[str, Any]], max_cases: int) -> List[Dict[str, Any]]:
    hard = []
    for idx, row in enumerate(rows, start=1):
        err = row_error(row)
        if not err["missing"] and not err["extra"]:
            continue
        hard.append(
            {
                "row_index": idx,
                "row": row,
                "missing": err["missing"],
                "extra": err["extra"],
                "score": len(err["missing"]) * 2 + len(err["extra"]),
            }
        )
    hard.sort(key=lambda item: (-item["score"], item["row_index"]))
    return hard[:max_cases]


def corpus_by_name(corpus: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(item.get("name")): item for item in corpus if item.get("name")}


def compact_message(text: str, limit: int) -> str:
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 20].rstrip() + "\n...[truncated]..."


def skill_reference(corpus_map: Dict[str, Dict[str, Any]], skills: List[str]) -> str:
    blocks = []
    for name in skills:
        item = corpus_map.get(name, {"name": name})
        blocks.append(
            "\n".join(
                [
                    f"- name: {name}",
                    f"  description: {item.get('description') or item.get('title') or ''}",
                    f"  excerpt: {item.get('excerpt', '')}",
                ]
            )
        )
    return "\n".join(blocks)


def make_prompt(
    *,
    prompt_id: str,
    case: Dict[str, Any],
    corpus_map: Dict[str, Dict[str, Any]],
    allowed_names: List[str],
    records_per_prompt: int,
    max_user_chars: int,
) -> Dict[str, Any]:
    row = case["row"]
    ideal = sorted(skill_set(row, "ideal_skills"))
    selected = sorted(skill_set(row, "selected_skills"))
    focus = sorted(set(ideal) | set(selected) | set(case["missing"]) | set(case["extra"]))
    focus = [skill for skill in focus if skill in allowed_names]

    prompt = f"""You are generating hard-case SkillRouter evolution data for an enterprise agent.

The goal is to fix routing mistakes around the original hard case below. Use only allowed skill names.

Allowed skills:
{json.dumps(allowed_names, ensure_ascii=False)}

Original hard case:
{compact_message(row.get("user_message", ""), max_user_chars)}

Ideal skills for the original case:
{json.dumps(ideal, ensure_ascii=False)}

Incorrect or candidate-selected skills:
{json.dumps(selected, ensure_ascii=False)}

Missing skills that must be reinforced:
{json.dumps(case["missing"], ensure_ascii=False)}

Extra skills that should become hard negatives:
{json.dumps(case["extra"], ensure_ascii=False)}

Relevant skill reference:
{skill_reference(corpus_map, focus)}

Generate exactly {records_per_prompt} JSON objects as a single JSON array. Do not output markdown.

Each object must have this schema:
{{
  "user_message": "realistic Chinese enterprise-agent request, not a verbatim copy unless necessary",
  "available_skills": ["subset of allowed skills"],
  "baseline_skills": ["skills a legacy router might choose, can include hard-negative noisy choices"],
  "router_selected_skills": ["candidate skills chosen by a hypothetical router"],
  "outcome": {{
    "status": "success|partial|failure",
    "user_accepted": true,
    "missing_skills": [],
    "unnecessary_skills": [],
    "human_corrected_skills": []
  }},
  "ideal_skills": ["best skill set according to the references"],
  "scenario_type": "success|missing_key_skill|unnecessary_skill|complex_multi_skill|failure",
  "reason": "short explanation of the label"
}}

Rules:
- Create variants that preserve the routing distinction from the hard case.
- Include hard negatives where tempting but wrong skills appear in baseline_skills or router_selected_skills and are marked as unnecessary.
- Include positive examples that require the missing skills.
- For long product/OA/NocoBase/evolution/debugging requests, distinguish modeling, ACL, workflow, plugin development, API reading, systematic debugging, and test-driven development.
- Do not include secrets, tokens, private keys, passwords, Authorization headers, or real personal data.
- All skill fields must use allowed skill names only.
"""
    return {
        "prompt_id": prompt_id,
        "records_per_prompt": records_per_prompt,
        "focus_skills": focus,
        "source_row": case["row_index"],
        "missing_skills": case["missing"],
        "extra_skills": case["extra"],
        "prompt": prompt,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build hard-case prompt pack from evaluation failures.")
    parser.add_argument("--corpus", default="skill_router_training/data_prod/prod_skill_corpus.json")
    parser.add_argument("--candidate", required=True, help="Evaluation JSONL for the candidate router.")
    parser.add_argument("--output-prompts", default="skill_router_training/data_prod/hard_case_router_prompts.jsonl")
    parser.add_argument("--max-cases", type=int, default=20)
    parser.add_argument("--records-per-case", type=int, default=20)
    parser.add_argument("--max-user-chars", type=int, default=4000)
    args = parser.parse_args()

    corpus = load_json(Path(args.corpus))
    corpus_map = corpus_by_name(corpus)
    allowed_names = sorted(corpus_map)
    candidate_rows = load_jsonl(Path(args.candidate))
    hard_cases = rank_hard_cases(candidate_rows, args.max_cases)
    prompts = [
        make_prompt(
            prompt_id=f"hard-router-{idx:03d}",
            case=case,
            corpus_map=corpus_map,
            allowed_names=allowed_names,
            records_per_prompt=args.records_per_case,
            max_user_chars=args.max_user_chars,
        )
        for idx, case in enumerate(hard_cases, start=1)
    ]
    save_jsonl(prompts, Path(args.output_prompts))

    print(f"candidate_rows: {len(candidate_rows)}")
    print(f"hard_cases: {len(hard_cases)}")
    print(f"prompts: {len(prompts)}")
    print(f"target_synthetic_records: {len(prompts) * args.records_per_case}")
    print(f"output_prompts: {args.output_prompts}")


if __name__ == "__main__":
    main()
