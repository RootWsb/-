#!/usr/bin/env python3
"""Call an OpenAI-compatible LLM API to batch-generate synthetic router records."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
from tqdm import tqdm

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from core.router_experience import save_jsonl  # noqa: E402
from scripts.convert_synthetic_router_records import convert_record, load_skill_names  # noqa: E402


SYSTEM_PROMPT = (
    "You are a strict JSON data generator. Output only valid JSON. "
    "Do not include markdown, explanations, or code fences."
)


def load_prompt_rows(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            value = json.loads(line)
            if isinstance(value, dict) and value.get("prompt"):
                rows.append(value)
    return rows


def append_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def normalize_api_base(api_base: str) -> str:
    return str(api_base or "").rstrip("/")


def call_chat_completion(
    *,
    api_base: str,
    api_key: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> str:
    url = f"{normalize_api_base(api_base)}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.encoding = "utf-8"
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code}: {compact_error(response.text)}")
    data = response.json()
    message = data["choices"][0]["message"]
    content = message.get("content") or message.get("reasoning_content") or ""
    if not content.strip():
        raise ValueError("LLM returned empty content.")
    return content


def compact_error(value: Any, limit: int = 300) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def parse_json_array(text: str) -> List[Dict[str, Any]]:
    """Parse a JSON array from plain JSON, fenced JSON, or surrounding prose."""
    text = str(text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        value = json.loads(text)
        return normalize_records(value)
    except json.JSONDecodeError:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        value = json.loads(text[start : end + 1])
        return normalize_records(value)

    # Last-resort JSON object extraction for models that emit JSONL-like text.
    records = []
    for match in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, flags=re.DOTALL):
        try:
            value = json.loads(match.group())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    if records:
        return records
    raise ValueError(f"Could not parse JSON records from response: {text[:500]}")


def normalize_records(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, dict):
        if isinstance(value.get("records"), list):
            value = value["records"]
        else:
            value = [value]
    if not isinstance(value, list):
        raise ValueError("Expected JSON array or object containing records.")
    return [row for row in value if isinstance(row, dict)]


def read_existing_prompt_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    seen = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            prompt_id = str(row.get("prompt_id") or "").strip()
            if prompt_id:
                seen.add(prompt_id)
    return seen


def build_records_for_prompt(
    *,
    row: Dict[str, Any],
    api_base: str,
    api_key: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
    retries: int,
    retry_sleep: float,
    raw_dir: Path,
) -> List[Dict[str, Any]]:
    prompt_id = str(row.get("prompt_id") or "prompt")
    last_error: Optional[Exception] = None
    raw_dir.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, retries + 1):
        try:
            content = call_chat_completion(
                api_base=api_base,
                api_key=api_key,
                model=model,
                prompt=str(row["prompt"]),
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            (raw_dir / f"{prompt_id}.txt").write_text(content, encoding="utf-8")
            records = parse_json_array(content)
            for idx, record in enumerate(records, start=1):
                record.setdefault("request_id", f"{prompt_id}-{idx:03d}")
                record["prompt_id"] = prompt_id
                record["focus_skills"] = row.get("focus_skills") or []
            return records
        except Exception as error:
            last_error = error
            (raw_dir / f"{prompt_id}.error.txt").write_text(str(error), encoding="utf-8")
            if attempt < retries:
                time.sleep(retry_sleep)
    raise RuntimeError(f"{prompt_id} failed after {retries} attempts: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-generate synthetic SkillRouter records with an external LLM.")
    parser.add_argument("--prompts", default=str(PACKAGE_ROOT / "data_prod" / "synthetic_router_prompts.jsonl"))
    parser.add_argument("--api-base", required=True, help="OpenAI-compatible base URL, for example https://api.example.com/v1")
    parser.add_argument("--api-key", default="", help="API key. If omitted, uses LLM_API_KEY.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-records", default=str(PACKAGE_ROOT / "data_prod" / "synthetic_llm_records.jsonl"))
    parser.add_argument("--experience-output", default="", help="Optional router_experience.v1 output path.")
    parser.add_argument("--skill-index", default=str(PACKAGE_ROOT / "data_prod" / "skill_index.json"))
    parser.add_argument("--raw-dir", default=str(PACKAGE_ROOT / "data_prod" / "synthetic_llm_raw"))
    parser.add_argument("--max-prompts", type=int, default=0, help="0 means all prompts.")
    parser.add_argument("--start-index", type=int, default=0, help="0-based prompt offset.")
    parser.add_argument("--temperature", type=float, default=0.4)
    parser.add_argument("--max-tokens", type=int, default=12000)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-sleep", type=float, default=5)
    parser.add_argument("--sleep", type=float, default=1, help="Delay between successful prompt calls.")
    parser.add_argument("--concurrency", type=int, default=1, help="Number of prompts to generate in parallel.")
    parser.add_argument("--resume", action="store_true", help="Skip prompt IDs already present in output-records.")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("LLM_API_KEY", "")
    if not api_key:
        raise SystemExit("Missing API key. Pass --api-key or set LLM_API_KEY.")

    prompt_rows = load_prompt_rows(Path(args.prompts))
    prompt_rows = prompt_rows[max(0, args.start_index) :]
    if args.max_prompts and args.max_prompts > 0:
        prompt_rows = prompt_rows[: args.max_prompts]

    output_records = Path(args.output_records)
    existing_prompt_ids = read_existing_prompt_ids(output_records) if args.resume else set()
    raw_dir = Path(args.raw_dir)

    pending_rows = []
    for row in prompt_rows:
        prompt_id = str(row.get("prompt_id") or "")
        if prompt_id in existing_prompt_ids:
            print(f"skip_existing: {prompt_id}")
        else:
            pending_rows.append(row)

    total_records = 0
    failed = 0
    concurrency = max(1, int(args.concurrency or 1))

    def generate_one(row: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
        prompt_id = str(row.get("prompt_id") or "")
        records = build_records_for_prompt(
            row=row,
            api_base=args.api_base,
            api_key=api_key,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
            retries=max(1, args.retries),
            retry_sleep=max(0, args.retry_sleep),
            raw_dir=raw_dir,
        )
        if args.sleep:
            time.sleep(max(0, args.sleep))
        return prompt_id, records

    if concurrency == 1:
        progress = tqdm(pending_rows, desc="Generating prompts", unit="prompt")
        for row in progress:
            prompt_id = str(row.get("prompt_id") or "")
            try:
                _, records = generate_one(row)
                append_jsonl(output_records, records)
                total_records += len(records)
                print(f"ok: {prompt_id} records={len(records)}")
            except Exception as error:
                failed += 1
                print(f"failed: {prompt_id} error={error}")
            progress.set_postfix(ok=len(pending_rows) - failed, failed=failed, records=total_records)
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {executor.submit(generate_one, row): str(row.get("prompt_id") or "") for row in pending_rows}
            with tqdm(total=len(futures), desc="Generating prompts", unit="prompt") as progress:
                for future in as_completed(futures):
                    prompt_id = futures[future]
                    try:
                        _, records = future.result()
                        append_jsonl(output_records, records)
                        total_records += len(records)
                        print(f"ok: {prompt_id} records={len(records)}")
                    except Exception as error:
                        failed += 1
                        print(f"failed: {prompt_id} error={error}")
                    progress.update(1)
                    progress.set_postfix(
                        ok=progress.n - failed,
                        failed=failed,
                        records=total_records,
                    )

    if args.experience_output:
        allowed = load_skill_names(Path(args.skill_index))
        generated = []
        with output_records.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle, start=1):
                if line.strip():
                    generated.append(convert_record(json.loads(line), index, allowed))
        save_jsonl(generated, Path(args.experience_output))
        rewarded = sum(1 for row in generated if row.get("reward") is not None)
        print(f"experience_output: {args.experience_output}")
        print(f"experience_records: {len(generated)}")
        print(f"rewarded: {rewarded}")

    print(f"prompts_attempted: {len(prompt_rows)}")
    print(f"prompts_submitted: {len(pending_rows)}")
    print(f"concurrency: {concurrency}")
    print(f"new_records: {total_records}")
    print(f"failed_prompts: {failed}")
    print(f"output_records: {args.output_records}")
    print(f"raw_dir: {args.raw_dir}")


if __name__ == "__main__":
    main()
