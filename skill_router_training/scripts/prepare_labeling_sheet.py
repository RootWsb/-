#!/usr/bin/env python3
"""
Create a human-friendly labeling sheet for Tianleixia log candidates.

This does not require knowing ideal skills up front. It combines:
- raw user messages from log candidates
- model predictions when available
- observed agents/plugins from logs
- the complete skill list from the current catalog
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))


def load_jsonl(path: Path) -> List[Dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_predictions(path: Path) -> Dict[str, Dict]:
    if not path.exists():
        return {}
    return {row.get("user_message", ""): row for row in load_jsonl(path)}


def load_catalog(path: Path) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def short(text: str, limit: int = 220) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "..."


def main():
    parser = argparse.ArgumentParser(description="Prepare labeling markdown sheet.")
    parser.add_argument(
        "--candidates",
        default=str(PACKAGE_ROOT / "data" / "tianleixia_log_candidates.jsonl"),
    )
    parser.add_argument(
        "--predictions",
        default=str(PACKAGE_ROOT / "data" / "ml_tianleixia_log_candidates.jsonl"),
    )
    parser.add_argument(
        "--catalog",
        default=str(PACKAGE_ROOT / "data" / "skill_catalog.json"),
    )
    parser.add_argument(
        "--output",
        default=str(PACKAGE_ROOT / "data" / "tianleixia_labeling_sheet.md"),
    )
    args = parser.parse_args()

    candidates = load_jsonl(Path(args.candidates))
    predictions = load_predictions(Path(args.predictions))
    catalog = load_catalog(Path(args.catalog))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Tianleixia Skill Labeling Sheet",
        "",
        "Use this sheet to decide `ideal_skills` for each real log request.",
        "The model prediction is only a suggestion; observed agents/plugins are runtime traces, not ground truth.",
        "",
        "## Skill Catalog",
        "",
    ]
    for item in catalog:
        lines.append(
            f"- `{item['skill_name']}` ({item.get('category', '')}): {short(item.get('description', ''))}"
        )

    lines.extend(["", "## Requests", ""])
    for idx, row in enumerate(candidates, 1):
        pred = predictions.get(row.get("user_message", ""), {})
        selected = pred.get("selected_skills", [])
        ideal = row.get("ideal_skills")
        if isinstance(ideal, list):
            ideal_text = ", ".join(f"`{s}`" for s in ideal) if ideal else "`[]`"
        else:
            ideal_text = "`TODO`"

        lines.extend([
            f"### {idx}. {row.get('workspace_name', '')}",
            "",
            "```text",
            row.get("user_message", ""),
            "```",
            "",
            f"- Model selected: {', '.join(f'`{s}`' for s in selected) if selected else '(none / not run)'}",
            f"- Observed agents: {', '.join(f'`{s}`' for s in row.get('observed_agents', [])) or '(none)'}",
            f"- Observed plugins: {', '.join(f'`{s}`' for s in row.get('observed_plugins', [])) or '(none)'}",
            f"- Ideal skills: {ideal_text}",
            f"- Label confidence: {row.get('label_confidence', 'manual')}",
            f"- Label reason: {row.get('label_reason', '')}",
            "- Notes:",
            "",
        ])

    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote: {output}")
    print(f"requests: {len(candidates)}")
    print(f"catalog skills: {len(catalog)}")


if __name__ == "__main__":
    main()
