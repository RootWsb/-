#!/usr/bin/env python3
"""
Extract Tianleixia workspace export logs into SkillRouter review candidates.

The output is intentionally a labeling file, not a scored test set:
`ideal_skills` is set to null so it cannot be mistaken for a no-skill label.
Fill `ideal_skills` manually before running model evaluation.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))


DEFAULT_IGNORED_DIRS = {
    ".claude",
    ".git",
    ".vscode",
    "skill_router_training",
    "uguardsec",
}


def detect_logs_root() -> Path:
    candidates = [
        Path(name)
        for name in os.listdir(".")
        if Path(name).is_dir() and name not in DEFAULT_IGNORED_DIRS
    ]
    if len(candidates) == 1:
        return candidates[0]
    for candidate in candidates:
        if any(candidate.rglob("messages/all-messages.jsonl")):
            return candidate
    raise SystemExit(
        "Unable to auto-detect logs root. Pass --logs-root explicitly."
    )


def iter_jsonl(path: Path) -> Iterable[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def workspace_label(chat_task_dir: Path) -> str:
    workspace_path = chat_task_dir / "workspace.json"
    if workspace_path.exists():
        try:
            data = load_json(workspace_path)
            name = data.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        except Exception:
            pass
    return chat_task_dir.name


def collect_plugin_runs(chat_task_dir: Path) -> List[str]:
    plugin_path = chat_task_dir / "raw" / "workspace_plugin_runs.json"
    if not plugin_path.exists():
        return []
    try:
        data = load_json(plugin_path)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    plugins = []
    for item in data:
        if isinstance(item, dict) and item.get("plugin_id"):
            plugins.append(str(item["plugin_id"]))
    return sorted(set(plugins))


def collect_agents(chat_task_dir: Path) -> List[str]:
    agents = set()
    runtime_path = chat_task_dir / "raw" / "go_runtime_events.json"
    if runtime_path.exists():
        try:
            data = load_json(runtime_path)
        except Exception:
            data = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("agent_id"):
                    agents.add(str(item["agent_id"]))

    messages_path = chat_task_dir / "messages" / "all-messages.jsonl"
    if messages_path.exists():
        for item in iter_jsonl(messages_path):
            if item.get("agent_id"):
                agents.add(str(item["agent_id"]))

    return sorted(agents)


def extract_messages(logs_root: Path, dedupe: bool) -> List[Dict]:
    rows: List[Dict] = []
    seen = set()

    for chat_task_dir in sorted(logs_root.rglob("*_chat_task")):
        if not chat_task_dir.is_dir():
            continue
        messages_path = chat_task_dir / "messages" / "all-messages.jsonl"
        if not messages_path.exists():
            continue

        label = workspace_label(chat_task_dir)
        plugins = collect_plugin_runs(chat_task_dir)
        agents = collect_agents(chat_task_dir)

        for message in iter_jsonl(messages_path):
            content = (message.get("content") or "").strip()
            if message.get("role") != "user" or not content:
                continue

            key = content if dedupe else message.get("id")
            if key in seen:
                continue
            seen.add(key)

            rows.append({
                "user_message": content,
                "ideal_skills": None,
                "source": "tianleixia_log",
                "workspace_name": label,
                "workspace_id": message.get("workspace_id"),
                "session_id": message.get("session_id"),
                "message_id": message.get("id"),
                "created_at": message.get("created_at"),
                "observed_agents": agents,
                "observed_plugins": plugins,
                "source_path": str(messages_path),
                "notes": "Fill ideal_skills manually before evaluation.",
            })

    return rows


def save_jsonl(rows: List[Dict], output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Extract Tianleixia logs into SkillRouter labeling candidates."
    )
    parser.add_argument("--logs-root", default=None)
    parser.add_argument(
        "--output",
        default=str(PACKAGE_ROOT / "data" / "tianleixia_log_candidates.jsonl"),
    )
    parser.add_argument(
        "--keep-duplicates",
        action="store_true",
        help="Keep duplicate user_message rows from repeated sessions.",
    )
    args = parser.parse_args()

    logs_root = Path(args.logs_root) if args.logs_root else detect_logs_root()
    output = Path(args.output)
    rows = extract_messages(logs_root, dedupe=not args.keep_duplicates)
    save_jsonl(rows, output)

    print(f"logs_root: {logs_root}")
    print(f"extracted_user_messages: {len(rows)}")
    print(f"output: {output}")
    for row in rows[:5]:
        print(f"- {row['user_message'][:120]} ({row['workspace_name']})")


if __name__ == "__main__":
    main()
