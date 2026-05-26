#!/usr/bin/env python3
"""Export real prod SKILL.md files into an LLM prompt pack for synthetic router data."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

PACKAGE_ROOT = Path(__file__).parent.parent
WORKSPACE_ROOT = PACKAGE_ROOT.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from core.utils import repair_mojibake  # noqa: E402


DEFAULT_SKILL_ROOT = WORKSPACE_ROOT / "artifacts" / "raw" / "prod"
DEFAULT_SKILL_INDEX = PACKAGE_ROOT / "data_prod" / "skill_index.json"
DEFAULT_OUTPUT_CORPUS = PACKAGE_ROOT / "data_prod" / "prod_skill_corpus.json"
DEFAULT_OUTPUT_PROMPTS = PACKAGE_ROOT / "data_prod" / "synthetic_router_prompts.jsonl"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(rows: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def parse_frontmatter(text: str) -> tuple[Dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    meta: Dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip("\"'")
    return meta, match.group(2)


def compact_text(value: str, limit: int) -> str:
    text = repair_prod_mojibake(" ".join(str(value or "").split()))
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def repair_prod_mojibake(value: str) -> str:
    """Repair common UTF-8-as-GBK mojibake found in exported prod skill files."""
    text = repair_mojibake(str(value or ""))
    suspicious_markers = ("鍦", "绯", "鎺", "闈", "㈡", "€", "鐨", "浣", "鏃", "嬭", "勮")
    suspicious = sum(text.count(marker) for marker in suspicious_markers)
    if suspicious < 2:
        return text
    try:
        repaired = text.encode("gbk").decode("utf-8")
    except UnicodeError:
        return text
    repaired_suspicious = sum(repaired.count(marker) for marker in suspicious_markers)
    return repaired if repaired_suspicious < suspicious else text


def extract_skill_doc(path: Path, root: Path) -> Dict[str, Any]:
    text = repair_prod_mojibake(path.read_text(encoding="utf-8", errors="ignore"))
    meta, body = parse_frontmatter(text)
    name = (meta.get("name") or path.parent.name).strip()
    description = compact_text(meta.get("description", ""), 400)
    title_match = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    title = compact_text(title_match.group(1), 120) if title_match else name
    excerpt = compact_text(body, 1400)
    return {
        "name": name,
        "description": description,
        "title": title,
        "excerpt": excerpt,
        "source_path": str(path.relative_to(root)),
        "body_length": len(body),
    }


def build_skill_corpus(skill_root: Path, skill_index: Dict[str, int]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for path in skill_root.rglob("SKILL.md"):
        doc = extract_skill_doc(path, skill_root)
        if doc["name"] not in skill_index:
            continue
        grouped.setdefault(doc["name"], []).append(doc)

    corpus = []
    for name, docs in grouped.items():
        docs.sort(key=lambda item: item["body_length"], reverse=True)
        primary = docs[0]
        descriptions = []
        seen_descriptions = set()
        for doc in docs:
            desc = doc.get("description", "")
            if desc and desc not in seen_descriptions:
                seen_descriptions.add(desc)
                descriptions.append(desc)
        corpus.append(
            {
                "name": name,
                "index": skill_index[name],
                "description": descriptions[0] if descriptions else "",
                "alternate_descriptions": descriptions[1:4],
                "title": primary["title"],
                "excerpt": primary["excerpt"],
                "source_count": len(docs),
                "source_paths": [doc["source_path"] for doc in docs[:5]],
            }
        )

    corpus.sort(key=lambda item: item["index"])
    return corpus


def make_prompt(prompt_id: int, corpus: List[Dict[str, Any]], focus_skills: List[str], records_per_prompt: int) -> Dict[str, Any]:
    allowed_names = [item["name"] for item in corpus]
    skill_blocks = []
    for item in corpus:
        marker = "FOCUS" if item["name"] in focus_skills else "support"
        skill_blocks.append(
            "\n".join(
                [
                    f"- name: {item['name']} ({marker})",
                    f"  description: {item.get('description') or item.get('title')}",
                    f"  excerpt: {item.get('excerpt', '')}",
                ]
            )
        )

    prompt = f"""You are generating synthetic SkillRouter evolution data for an enterprise agent.

Use only the allowed skill names listed below. Ground the task scenarios in the skill descriptions and excerpts.

Allowed skills:
{json.dumps(allowed_names, ensure_ascii=False)}

Focus skills for this batch:
{json.dumps(focus_skills, ensure_ascii=False)}

Skill reference:
{chr(10).join(skill_blocks)}

Generate exactly {records_per_prompt} JSON objects as a single JSON array. Do not output markdown.

Each object must have this schema:
{{
  "user_message": "realistic user request in Chinese, with enough context to route skills",
  "available_skills": ["subset of allowed skills"],
  "baseline_skills": ["skills a legacy router might choose, can be noisy"],
  "router_selected_skills": ["candidate skills chosen by a hypothetical router"],
  "outcome": {{
    "status": "success|partial|failure",
    "user_accepted": true,
    "missing_skills": [],
    "unnecessary_skills": [],
    "human_corrected_skills": []
  }},
  "ideal_skills": ["best skill set according to the references"],
  "scenario_type": "success|missing_key_skill|unnecessary_skill|no_skill|complex_multi_skill|failure",
  "reason": "short explanation of the label"
}}

Rules:
- Include a mix of successful routes, missing-key-skill cases, unnecessary-skill cases, complex multi-skill tasks, and no-skill/low-skill tasks.
- At least half of the records should involve one or more focus skills.
- `ideal_skills`, `available_skills`, `baseline_skills`, `router_selected_skills`, and all outcome skill lists must use allowed skill names only.
- If `status` is success, `missing_skills` should normally be empty.
- If the hypothetical router missed a required skill, set status to partial or failure and include it in `missing_skills`.
- If the hypothetical router selected irrelevant skills, include them in `unnecessary_skills`.
- If a human correction is obvious, set `human_corrected_skills` to the ideal final skill list.
- Do not include secrets, tokens, private URLs, or real personal data.
"""
    return {
        "prompt_id": f"synthetic-router-{prompt_id:03d}",
        "records_per_prompt": records_per_prompt,
        "focus_skills": focus_skills,
        "prompt": prompt,
    }


def build_prompts(corpus: List[Dict[str, Any]], num_prompts: int, records_per_prompt: int, focus_size: int) -> List[Dict[str, Any]]:
    names = [item["name"] for item in corpus]
    prompts = []
    for idx in range(num_prompts):
        start = (idx * focus_size) % max(1, len(names))
        focus = [names[(start + offset) % len(names)] for offset in range(min(focus_size, len(names)))]
        prompts.append(make_prompt(idx + 1, corpus, focus, records_per_prompt))
    return prompts


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an LLM prompt pack from real prod SKILL.md files.")
    parser.add_argument("--skill-root", default=str(DEFAULT_SKILL_ROOT))
    parser.add_argument("--skill-index", default=str(DEFAULT_SKILL_INDEX))
    parser.add_argument("--output-corpus", default=str(DEFAULT_OUTPUT_CORPUS))
    parser.add_argument("--output-prompts", default=str(DEFAULT_OUTPUT_PROMPTS))
    parser.add_argument("--num-prompts", type=int, default=10)
    parser.add_argument("--records-per-prompt", type=int, default=20)
    parser.add_argument("--focus-size", type=int, default=4)
    args = parser.parse_args()

    skill_root = Path(args.skill_root)
    skill_index = load_json(Path(args.skill_index))
    corpus = build_skill_corpus(skill_root, skill_index)
    prompts = build_prompts(
        corpus,
        num_prompts=max(1, args.num_prompts),
        records_per_prompt=max(1, args.records_per_prompt),
        focus_size=max(1, args.focus_size),
    )

    save_json(corpus, Path(args.output_corpus))
    append_jsonl(prompts, Path(args.output_prompts))

    missing = [name for name in skill_index if name not in {item["name"] for item in corpus}]
    print(f"skill_root: {skill_root}")
    print(f"indexed_skills: {len(skill_index)}")
    print(f"corpus_skills: {len(corpus)}")
    print(f"missing_from_prod_skill_files: {len(missing)}")
    if missing:
        print("missing_names: " + ", ".join(missing[:20]))
    print(f"prompts: {len(prompts)}")
    print(f"target_synthetic_records: {len(prompts) * max(1, args.records_per_prompt)}")
    print(f"output_corpus: {args.output_corpus}")
    print(f"output_prompts: {args.output_prompts}")


if __name__ == "__main__":
    main()
