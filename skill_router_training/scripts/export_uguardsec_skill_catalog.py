#!/usr/bin/env python3
"""
Export a SkillRouter catalog from uguardsec / agent-config-service skill data.

Supported inputs:
- a team package directory or tar.gz that contains */skills/<skill>/SKILL.md
- an agent-config-service archive directory or tar.gz with data/skills.jsonl and
  data/skill_text_documents.jsonl
- an API JSON response saved from /api/skills
- a live /api/skills endpoint
"""

import argparse
import json
import re
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Optional, Tuple

PACKAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from core.utils import repair_mojibake


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
WHEN_PATTERNS = (
    "when to use",
    "适用",
    "使用场景",
    "触发",
    "何时使用",
    "use this",
    "用于",
)


def load_jsonl(path: Path) -> List[Dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_text(path: Path) -> str:
    return repair_mojibake(path.read_text(encoding="utf-8", errors="ignore"))


def strip_frontmatter(markdown: str) -> Tuple[Dict[str, str], str]:
    metadata: Dict[str, str] = {}
    match = FRONTMATTER_RE.match(markdown)
    if not match:
        return metadata, markdown

    raw = match.group(1)
    body = markdown[match.end() :]
    current_key = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if re.match(r"^\s", line) and current_key:
            metadata[current_key] = (metadata[current_key] + " " + line.strip()).strip()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value in {">", "|"}:
            value = ""
        metadata[key] = value
        current_key = key
    return metadata, body


def first_heading(markdown: str) -> str:
    match = HEADING_RE.search(markdown)
    return match.group(2).strip() if match else ""


def normalize_space(text: str, limit: int = 1200) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit]


def section_after_heading(markdown: str, title_patterns: Iterable[str]) -> str:
    headings = list(HEADING_RE.finditer(markdown))
    lowered_patterns = [pattern.lower() for pattern in title_patterns]
    for index, heading in enumerate(headings):
        title = heading.group(2).strip().lower()
        if not any(pattern in title for pattern in lowered_patterns):
            continue
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(markdown)
        return normalize_space(markdown[start:end])
    return ""


def infer_category_from_path(path: Path, root: Path) -> str:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    lowered = [part.lower() for part in parts]
    if "system" in lowered:
        return "system"
    if "agents" in lowered:
        return "agent"
    if "skills" in lowered:
        return "skill"
    return "unknown"


def skill_from_markdown(skill_md: Path, root: Path) -> Dict:
    content = read_text(skill_md)
    metadata, body = strip_frontmatter(content)
    skill_name = skill_md.parent.name
    display_name = metadata.get("name") or first_heading(body) or skill_name
    description = metadata.get("description") or ""
    if not description:
        description = section_after_heading(body, ("description", "简介", "说明", "能力"))
    if not description:
        description = normalize_space(body, limit=400)

    when_to_use = section_after_heading(body, WHEN_PATTERNS)
    if not when_to_use:
        when_to_use = description

    return {
        "skill_name": skill_name,
        "category": infer_category_from_path(skill_md, root),
        "display_name": display_name,
        "description": normalize_space(description, limit=600),
        "when_to_use": normalize_space(when_to_use, limit=800),
        "source_path": skill_md.relative_to(root).as_posix() if skill_md.is_relative_to(root) else str(skill_md),
    }


def scan_skill_markdown(root: Path) -> List[Dict]:
    rows = []
    for skill_md in sorted(root.rglob("SKILL.md")):
        parts = {part.lower() for part in skill_md.parts}
        if "skills" not in parts:
            continue
        rows.append(skill_from_markdown(skill_md, root))
    return rows


def archive_records_from_dir(root: Path) -> Optional[List[Dict]]:
    skills_path = root / "data" / "skills.jsonl"
    docs_path = root / "data" / "skill_text_documents.jsonl"
    if not skills_path.exists() or not docs_path.exists():
        return None

    skills = load_jsonl(skills_path)
    docs = load_jsonl(docs_path)
    docs_by_skill: Dict[str, List[Dict]] = {}
    for doc in docs:
        docs_by_skill.setdefault(str(doc.get("skill_id")), []).append(doc)

    rows = []
    for skill in skills:
        key = str(skill.get("key") or skill.get("name") or "").strip()
        if not key:
            continue
        skill_docs = docs_by_skill.get(str(skill.get("id")), [])
        skill_doc = next(
            (
                doc
                for doc in skill_docs
                if str(doc.get("relative_path") or "").lower().endswith("skill.md")
                or doc.get("document_type") == "skill"
            ),
            None,
        )
        content = str(skill_doc.get("content") or "") if skill_doc else ""
        _, body = strip_frontmatter(repair_mojibake(content))
        when_to_use = section_after_heading(body, WHEN_PATTERNS)
        description = str(skill.get("description") or "")
        if not description:
            description = normalize_space(body, limit=400)
        rows.append(
            {
                "skill_name": key,
                "category": str(skill.get("category") or "unknown"),
                "display_name": str(skill.get("name") or key),
                "description": normalize_space(repair_mojibake(description), limit=600),
                "when_to_use": normalize_space(when_to_use or description or body, limit=800),
                "source_path": "archive:data/skills.jsonl",
                "version": skill.get("version"),
                "scope": skill.get("scope"),
            }
        )
    return rows


def api_records_from_json(payload) -> List[Dict]:
    if isinstance(payload, dict) and "data" in payload:
        payload = payload["data"]
    if isinstance(payload, dict) and "items" in payload:
        payload = payload["items"]
    if not isinstance(payload, list):
        raise ValueError("API payload must be a list or contain data/items list")

    rows = []
    for skill in payload:
        key = str(skill.get("key") or skill.get("skill_name") or skill.get("name") or "").strip()
        if not key:
            continue
        docs = skill.get("text_documents") or []
        skill_doc = next(
            (
                doc
                for doc in docs
                if str(doc.get("relative_path") or "").lower().endswith("skill.md")
                or doc.get("document_type") == "skill"
            ),
            None,
        )
        content = str(skill_doc.get("content") or "") if skill_doc else ""
        _, body = strip_frontmatter(repair_mojibake(content))
        description = skill.get("description") or normalize_space(body, limit=400)
        rows.append(
            {
                "skill_name": key,
                "category": str(skill.get("category") or "unknown"),
                "display_name": str(skill.get("name") or key),
                "description": normalize_space(repair_mojibake(str(description)), limit=600),
                "when_to_use": normalize_space(
                    section_after_heading(body, WHEN_PATTERNS) or str(description) or body,
                    limit=800,
                ),
                "source_path": "api",
                "version": skill.get("version"),
                "scope": skill.get("scope"),
            }
        )
    return rows


def safe_extract_tar(archive_path: Path, target_dir: Path):
    with tarfile.open(archive_path, "r:*") as tar:
        for member in tar.getmembers():
            member_path = PurePosixPath(member.name)
            if member_path.is_absolute() or any(part in {"", ".", ".."} for part in member_path.parts):
                raise ValueError(f"Unsafe tar path: {member.name}")
        tar.extractall(target_dir)


def rows_from_path(path: Path) -> List[Dict]:
    if path.is_dir():
        archive_rows = archive_records_from_dir(path)
        if archive_rows is not None:
            return archive_rows
        return scan_skill_markdown(path)

    suffixes = "".join(path.suffixes).lower()
    if suffixes.endswith(".tar.gz") or path.suffix.lower() in {".tgz", ".tar"}:
        with tempfile.TemporaryDirectory(prefix="uguardsec-catalog-") as tmp:
            tmp_dir = Path(tmp)
            safe_extract_tar(path, tmp_dir)
            archive_rows = archive_records_from_dir(tmp_dir)
            if archive_rows is not None:
                return archive_rows
            return scan_skill_markdown(tmp_dir)

    if path.suffix.lower() in {".json", ".jsonl"}:
        if path.suffix.lower() == ".jsonl":
            return api_records_from_json(load_jsonl(path))
        with open(path, "r", encoding="utf-8") as f:
            return api_records_from_json(json.load(f))

    raise ValueError(f"Unsupported input: {path}")


def rows_from_api(url: str, token: str = "", user_id: str = "", admin_token: str = "") -> List[Dict]:
    import requests

    headers = {}
    if token:
        headers["X-Agent-Config-Token"] = token
    if user_id:
        headers["X-User-Id"] = user_id
    if admin_token:
        headers["X-Agent-Config-Admin-Token"] = admin_token
    response = requests.get(url.rstrip("/") + "/api/skills", headers=headers, timeout=60)
    response.raise_for_status()
    return api_records_from_json(response.json())


def dedupe_rows(rows: List[Dict]) -> List[Dict]:
    by_name: Dict[str, Dict] = {}
    for row in rows:
        name = str(row.get("skill_name") or "").strip()
        if not name:
            continue
        existing = by_name.get(name)
        if existing is None:
            by_name[name] = row
            continue
        old_score = len(existing.get("description", "")) + len(existing.get("when_to_use", ""))
        new_score = len(row.get("description", "")) + len(row.get("when_to_use", ""))
        if new_score > old_score:
            by_name[name] = row
    return [by_name[name] for name in sorted(by_name)]


def main():
    parser = argparse.ArgumentParser(description="Export uguardsec skills to SkillRouter catalog.")
    parser.add_argument("--input", action="append", default=[], help="Directory, tar.gz, JSON, or JSONL input.")
    parser.add_argument("--api-url", default="", help="Base URL of running agent-config-service.")
    parser.add_argument("--token", default="", help="X-Agent-Config-Token for API mode.")
    parser.add_argument("--user-id", default="", help="X-User-Id for API mode.")
    parser.add_argument("--admin-token", default="", help="X-Agent-Config-Admin-Token for API mode.")
    parser.add_argument(
        "--output-catalog",
        default=str(PACKAGE_ROOT / "data" / "skill_catalog_uguardsec.json"),
    )
    parser.add_argument(
        "--output-index",
        default=str(PACKAGE_ROOT / "data" / "skill_index_uguardsec.json"),
    )
    args = parser.parse_args()

    rows: List[Dict] = []
    for value in args.input:
        rows.extend(rows_from_path(Path(value)))
    if args.api_url:
        rows.extend(rows_from_api(args.api_url, args.token, args.user_id, args.admin_token))

    rows = dedupe_rows(rows)
    skill_index = {row["skill_name"]: idx for idx, row in enumerate(rows)}

    write_json(rows, Path(args.output_catalog))
    write_json(skill_index, Path(args.output_index))

    print(f"skills: {len(rows)}")
    print(f"catalog: {args.output_catalog}")
    print(f"index: {args.output_index}")
    if rows:
        print("sample:")
        for row in rows[:5]:
            print(f"  - {row['skill_name']} ({row.get('category', '')}): {row.get('description', '')[:80]}")
    else:
        print("No skills found. Provide a team package/archive/API export that contains skill records.")


if __name__ == "__main__":
    main()
