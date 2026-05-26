#!/usr/bin/env python3
"""Router experience records and reward shaping for SkillRouter evolution."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "router_experience.v1"


def unique_skills(value: Any) -> List[str]:
    """Normalize a skill list while preserving first-seen order."""
    if not isinstance(value, list):
        return []
    output: List[str] = []
    seen = set()
    for item in value:
        if isinstance(item, dict):
            name = str(item.get("skill_name") or item.get("skill") or item.get("name") or "").strip()
        else:
            name = str(item or "").strip()
        if name and name not in seen:
            seen.add(name)
            output.append(name)
    return output


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass
class RouterOutcome:
    """Post-task signal used to score one router decision."""

    status: str = "unknown"
    user_accepted: Optional[bool] = None
    human_corrected_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    unnecessary_skills: List[str] = field(default_factory=list)
    tool_call_count: Optional[int] = None
    duration_ms: Optional[float] = None
    notes: str = ""

    @classmethod
    def from_dict(cls, value: Optional[Dict[str, Any]]) -> "RouterOutcome":
        value = value if isinstance(value, dict) else {}
        return cls(
            status=str(value.get("status") or "unknown").lower(),
            user_accepted=_optional_bool(value.get("user_accepted")),
            human_corrected_skills=unique_skills(value.get("human_corrected_skills")),
            missing_skills=unique_skills(value.get("missing_skills")),
            unnecessary_skills=unique_skills(value.get("unnecessary_skills")),
            tool_call_count=_optional_int(value.get("tool_call_count")),
            duration_ms=_optional_float(value.get("duration_ms")),
            notes=str(value.get("notes") or "")[:500],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "user_accepted": self.user_accepted,
            "human_corrected_skills": self.human_corrected_skills,
            "missing_skills": self.missing_skills,
            "unnecessary_skills": self.unnecessary_skills,
            "tool_call_count": self.tool_call_count,
            "duration_ms": self.duration_ms,
            "notes": self.notes,
        }


@dataclass
class RouterExperience:
    """One state-action-outcome item for later router retraining or review."""

    request_id: str = ""
    task_id: str = ""
    query_sha256: str = ""
    available_skills: List[str] = field(default_factory=list)
    baseline_skills: List[str] = field(default_factory=list)
    router_selected_skills: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    threshold: Optional[float] = None
    top_k: Optional[int] = None
    user_message_redacted: str = ""
    outcome: RouterOutcome = field(default_factory=RouterOutcome)
    reward: Optional[float] = None
    learning_target_skills: List[str] = field(default_factory=list)
    label_source: str = "none"
    confidence: str = "low"
    memory_refs: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "created_at": self.created_at,
            "request_id": self.request_id,
            "task_id": self.task_id,
            "query_sha256": self.query_sha256,
            "query_text_allowed": bool(self.user_message_redacted),
            "user_message_redacted": self.user_message_redacted,
            "available_skills": self.available_skills,
            "baseline_skills": self.baseline_skills,
            "router_selected_skills": self.router_selected_skills,
            "scores": self.scores,
            "threshold": self.threshold,
            "top_k": self.top_k,
            "outcome": self.outcome.to_dict(),
            "reward": self.reward,
            "learning_target_skills": self.learning_target_skills,
            "label_source": self.label_source,
            "confidence": self.confidence,
            "memory_refs": self.memory_refs,
        }


def compute_reward(
    selected_skills: Iterable[str],
    baseline_skills: Iterable[str],
    outcome: RouterOutcome,
) -> Optional[float]:
    """Return a bounded reward, or None when there is no useful outcome signal."""
    selected = set(selected_skills)
    baseline = set(baseline_skills)
    has_signal = (
        outcome.status in {"success", "partial", "failure"}
        or outcome.user_accepted is not None
        or bool(outcome.human_corrected_skills)
        or bool(outcome.missing_skills)
        or bool(outcome.unnecessary_skills)
    )
    if not has_signal:
        return None

    reward = 0.0
    if outcome.status == "success":
        reward += 0.8
    elif outcome.status == "partial":
        reward += 0.25
    elif outcome.status == "failure":
        reward -= 0.8

    if outcome.user_accepted is True:
        reward += 0.2
    elif outcome.user_accepted is False:
        reward -= 0.5

    reward -= min(0.75, 0.25 * len(outcome.missing_skills))
    reward -= min(0.40, 0.10 * len(outcome.unnecessary_skills))

    if baseline:
        delta = len(selected) - len(baseline)
        if outcome.status in {"success", "partial"} and delta < 0:
            reward += min(0.20, 0.05 * abs(delta))
        elif delta > 0:
            reward -= min(0.20, 0.04 * delta)

    if outcome.tool_call_count is not None and outcome.tool_call_count > 30:
        reward -= 0.05

    return round(clamp(reward), 4)


def derive_learning_target(
    selected_skills: Iterable[str],
    outcome: RouterOutcome,
) -> tuple[List[str], str, str]:
    """Choose a training label candidate and annotate its reliability."""
    selected = unique_skills(list(selected_skills))
    if outcome.human_corrected_skills:
        return outcome.human_corrected_skills, "human_corrected_skills", "high"

    if outcome.status == "success" and not outcome.missing_skills:
        unnecessary = set(outcome.unnecessary_skills)
        target = [skill for skill in selected if skill not in unnecessary]
        return target, "successful_route", "medium"

    if outcome.status == "partial" and outcome.missing_skills:
        merged = selected + [skill for skill in outcome.missing_skills if skill not in selected]
        unnecessary = set(outcome.unnecessary_skills)
        target = [skill for skill in merged if skill not in unnecessary]
        return target, "partial_with_corrections", "medium"

    return [], "none", "low"


def experience_from_route_record(
    route_record: Dict[str, Any],
    outcome_record: Optional[Dict[str, Any]] = None,
) -> RouterExperience:
    """Build a RouterExperience from sidecar/plugin audit plus optional outcome."""
    outcome = RouterOutcome.from_dict(outcome_record)
    shadow = route_record.get("shadow_comparison") if isinstance(route_record.get("shadow_comparison"), dict) else {}
    selected = unique_skills(
        route_record.get("selected_skill_names")
        or route_record.get("router_selected_skills")
        or route_record.get("selected_skills")
    )
    baseline = unique_skills(route_record.get("baseline_skills") or shadow.get("baseline_skills"))
    target, label_source, confidence = derive_learning_target(selected, outcome)
    return RouterExperience(
        request_id=str(route_record.get("request_id") or outcome_record.get("request_id") if outcome_record else route_record.get("request_id") or ""),
        task_id=str((outcome_record or {}).get("task_id") or route_record.get("task_id") or ""),
        query_sha256=str(route_record.get("query_sha256") or (outcome_record or {}).get("query_sha256") or ""),
        available_skills=unique_skills(route_record.get("available_skills")),
        baseline_skills=baseline,
        router_selected_skills=selected,
        scores=_scores_from_route(route_record),
        threshold=_optional_float(route_record.get("threshold")),
        top_k=_optional_int(route_record.get("top_k")),
        user_message_redacted=_redacted_text(route_record, outcome_record),
        outcome=outcome,
        reward=compute_reward(selected, baseline, outcome),
        learning_target_skills=target,
        label_source=label_source,
        confidence=confidence,
        memory_refs=unique_skills((outcome_record or {}).get("memory_refs")),
    )


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path or not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def save_jsonl(rows: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def index_outcomes(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        for key in ("request_id", "query_sha256", "task_id"):
            value = str(row.get(key) or "").strip()
            if value and value not in indexed:
                indexed[value] = row
    return indexed


def match_outcome(route_record: Dict[str, Any], outcomes: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for key in ("request_id", "query_sha256", "task_id"):
        value = str(route_record.get(key) or "").strip()
        if value and value in outcomes:
            return outcomes[value]
    return None


def _scores_from_route(record: Dict[str, Any]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    selected = record.get("selected_skills")
    if isinstance(selected, list):
        for item in selected:
            if not isinstance(item, dict):
                continue
            name = str(item.get("skill_name") or item.get("skill") or "").strip()
            score = _optional_float(item.get("score"))
            if name and score is not None:
                scores[name] = score
    return scores


def _redacted_text(route_record: Dict[str, Any], outcome_record: Optional[Dict[str, Any]]) -> str:
    """Return a bounded, explicitly redacted training text if one is available."""
    for source in (route_record, outcome_record or {}):
        for key in (
            "user_message_redacted",
            "redacted_user_message",
            "query_text_redacted",
            "redacted_query_text",
            "request_summary",
            "notes_redacted",
        ):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:8000]
    return ""


def _optional_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _optional_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if str(value).lower() in {"true", "1", "yes"}:
        return True
    if str(value).lower() in {"false", "0", "no"}:
        return False
    return None
