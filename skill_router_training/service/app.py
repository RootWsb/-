#!/usr/bin/env python3
"""Serve a trained SkillRouter classifier as a shadow-friendly HTTP sidecar."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PACKAGE_ROOT.parent
sys.path.insert(0, str(PACKAGE_ROOT))

DEFAULT_CHECKPOINT = PACKAGE_ROOT / "checkpoints" / "skill_router_prod" / "best"
DEFAULT_SKILL_INDEX = PACKAGE_ROOT / "data_prod" / "skill_index.json"
DEFAULT_DASHBOARD_DIR = PACKAGE_ROOT / "runtime" / "dashboard"
WEBUI_DIR = PACKAGE_ROOT / "service" / "webui"


@dataclass
class RouterSettings:
    checkpoint: Path = DEFAULT_CHECKPOINT
    skill_index: Path = DEFAULT_SKILL_INDEX
    embedding_model: Optional[str] = None
    device: str = "auto"
    threshold: float = 0.5
    top_k: int = 8
    local_files_only: bool = True
    audit_log: Optional[Path] = None
    dashboard_dir: Optional[Path] = DEFAULT_DASHBOARD_DIR


class RouteRequest(BaseModel):
    query: Optional[str] = None
    user_message: Optional[str] = None
    request_id: Optional[str] = None
    available_skills: Optional[List[str]] = None
    baseline_skills: Optional[List[str]] = None
    threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=1)


def _load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_embedding_model(checkpoint: Path, override: Optional[str]) -> str:
    """Prefer an explicit or saved model path, then the bundled workspace model."""
    saved_config = _load_json(checkpoint / "config.json")
    requested = override or saved_config["embedding_model"]
    requested_path = Path(requested)
    candidate = requested_path if requested_path.is_absolute() else WORKSPACE_ROOT / requested_path
    if candidate.exists():
        return str(candidate)

    bundled_model = WORKSPACE_ROOT / "models"
    if (bundled_model / "config.json").exists():
        return str(bundled_model)

    return requested


class DashboardStore:
    """Persist central routing controls and privacy-safe plugin event data."""

    def __init__(self, root: Path, threshold: float, top_k: int):
        self.root = root
        self.policy_path = root / "policy.json"
        self.events_path = root / "plugin_events.jsonl"
        self.default_policy = {
            "routing_enabled": True,
            "enforce_parameters": False,
            "threshold": threshold,
            "top_k": top_k,
        }
        self._lock = threading.Lock()

    def policy(self) -> Dict[str, Any]:
        saved = {}
        try:
            saved = _load_json(self.policy_path)
        except (OSError, json.JSONDecodeError):
            pass
        policy = dict(self.default_policy)
        if isinstance(saved, dict):
            policy.update(self._validated_policy(saved))
        return policy

    def save_policy(self, value: Dict[str, Any]) -> Dict[str, Any]:
        policy = self.policy()
        policy.update(self._validated_policy(value))
        self.root.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self.policy_path.write_text(
                json.dumps(policy, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return policy

    @staticmethod
    def _validated_policy(value: Dict[str, Any]) -> Dict[str, Any]:
        output = {}
        for key in ("routing_enabled", "enforce_parameters"):
            if key in value and isinstance(value[key], bool):
                output[key] = value[key]
        if "threshold" in value:
            try:
                output["threshold"] = max(0.0, min(float(value["threshold"]), 1.0))
            except (TypeError, ValueError):
                pass
        if "top_k" in value:
            try:
                output["top_k"] = max(1, min(int(value["top_k"]), 50))
            except (TypeError, ValueError):
                pass
        return output

    @staticmethod
    def _skills(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        output = []
        seen = set()
        for skill in value:
            name = str(skill or "").strip()
            if name and name not in seen:
                seen.add(name)
                output.append(name)
        return output

    def append_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        shadow = event.get("shadow_comparison") if isinstance(event.get("shadow_comparison"), dict) else {}
        record = {
            "timestamp": event.get("timestamp") or time.time(),
            "request_id": str(event.get("request_id") or "")[:160],
            "plugin_id": str(event.get("plugin_id") or "skill-router")[:80],
            "ok": bool(event.get("ok", False)),
            "selected_skill_names": self._skills(event.get("selected_skill_names")),
            "shadow_comparison": {
                "baseline_skills": self._skills(shadow.get("baseline_skills")),
                "suggested_additions": self._skills(shadow.get("suggested_additions")),
                "suggested_removals": self._skills(shadow.get("suggested_removals")),
            } if shadow else None,
            "latency_ms": self._number(event.get("latency_ms")),
            "plugin_latency_ms": self._number(event.get("plugin_latency_ms")),
            "error": str(event.get("error") or "")[:300],
            "skipped": str(event.get("skipped") or "")[:120],
            "active_model": str(event.get("active_model") or "")[:300],
        }
        self.root.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with open(self.events_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    @staticmethod
    def _number(value: Any) -> Optional[float]:
        try:
            return round(float(value), 2) if value is not None else None
        except (TypeError, ValueError):
            return None

    def events(self, limit: int = 1000) -> List[Dict[str, Any]]:
        try:
            with open(self.events_path, "r", encoding="utf-8") as handle:
                rows = [json.loads(line) for line in handle if line.strip()]
        except (OSError, json.JSONDecodeError):
            return []
        return rows[-max(1, min(limit, 10000)):]

    def summary(self, limit: int = 1000) -> Dict[str, Any]:
        events = self.events(limit)
        comparable = [
            row for row in events
            if isinstance(row.get("shadow_comparison"), dict)
            and row["shadow_comparison"].get("baseline_skills") is not None
        ]
        before_counts = [len(row["shadow_comparison"]["baseline_skills"]) for row in comparable]
        after_counts = [len(row.get("selected_skill_names") or []) for row in comparable]
        additions = Counter()
        removals = Counter()
        for row in comparable:
            additions.update(row["shadow_comparison"].get("suggested_additions") or [])
            removals.update(row["shadow_comparison"].get("suggested_removals") or [])
        router_latency = [row["latency_ms"] for row in events if row.get("latency_ms") is not None]
        plugin_latency = [row["plugin_latency_ms"] for row in events if row.get("plugin_latency_ms") is not None]
        successes = sum(1 for row in events if row.get("ok"))
        before_avg = sum(before_counts) / len(before_counts) if before_counts else None
        after_avg = sum(after_counts) / len(after_counts) if after_counts else None
        return {
            "event_count": len(events),
            "comparable_count": len(comparable),
            "ok_rate": successes / len(events) if events else None,
            "avg_selected_before": before_avg,
            "avg_selected_after": after_avg,
            "selected_reduction": (
                (before_avg - after_avg) / before_avg
                if before_avg not in (None, 0) and after_avg is not None else None
            ),
            "latency": {
                "router_p50_ms": self._percentile(router_latency, 50),
                "router_p95_ms": self._percentile(router_latency, 95),
                "plugin_p50_ms": self._percentile(plugin_latency, 50),
                "plugin_p95_ms": self._percentile(plugin_latency, 95),
            },
            "top_additions": [{"skill": name, "count": count} for name, count in additions.most_common(8)],
            "top_removals": [{"skill": name, "count": count} for name, count in removals.most_common(8)],
            "series": [
                {
                    "timestamp": row.get("timestamp"),
                    "before_count": len(row["shadow_comparison"]["baseline_skills"]),
                    "after_count": len(row.get("selected_skill_names") or []),
                }
                for row in comparable[-40:]
            ],
        }

    @staticmethod
    def _percentile(values: List[float], percentile: int) -> Optional[float]:
        if not values:
            return None
        ordered = sorted(values)
        rank = (len(ordered) - 1) * percentile / 100
        low = int(rank)
        high = min(low + 1, len(ordered) - 1)
        fraction = rank - low
        return round(ordered[low] + (ordered[high] - ordered[low]) * fraction, 2)


class RouterRuntime:
    """Loaded classifier and request-level filtering for sidecar inference."""

    def __init__(self, settings: RouterSettings, model: Any = None):
        self.settings = settings
        self.skill_index: Dict[str, int] = _load_json(settings.skill_index)
        self.skill_names = [
            name for name, _ in sorted(self.skill_index.items(), key=lambda item: item[1])
        ]
        self.checkpoint_config = _load_json(settings.checkpoint / "config.json")
        expected_skills = int(self.checkpoint_config["num_skills"])
        if expected_skills != len(self.skill_names):
            raise ValueError(
                f"Checkpoint expects {expected_skills} skills, index contains {len(self.skill_names)}."
            )

        self.embedding_model = resolve_embedding_model(settings.checkpoint, settings.embedding_model)
        self.device = self._resolve_device(settings.device)
        self._inference_lock = threading.Lock()
        self._audit_lock = threading.Lock()
        self.dashboard = (
            DashboardStore(settings.dashboard_dir, settings.threshold, settings.top_k)
            if settings.dashboard_dir is not None
            else None
        )
        self.model = model if model is not None else self._load_model()

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device != "auto":
            return device
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    def _load_model(self):
        try:
            from core.model import SkillRouter

            return SkillRouter.load_classifier(
                str(self.settings.checkpoint),
                device=self.device,
                embedding_model=self.embedding_model,
                local_files_only=self.settings.local_files_only,
            )
        except Exception as error:
            raise RuntimeError(
                "Failed to load SkillRouter. Verify that torch, transformers, "
                "the checkpoint, and the local embedding model are installed and readable."
            ) from error

    @staticmethod
    def _unique_skills(skills: Optional[List[str]]) -> Optional[List[str]]:
        if skills is None:
            return None
        seen = set()
        unique = []
        for skill in skills:
            if skill not in seen:
                seen.add(skill)
                unique.append(skill)
        return unique

    def info(self) -> Dict[str, Any]:
        return {
            "status": "ready",
            "checkpoint": str(self.settings.checkpoint),
            "embedding_model": self.embedding_model,
            "device": self.device,
            "num_skills": len(self.skill_names),
            "default_threshold": self.settings.threshold,
            "default_top_k": self.settings.top_k,
        }

    def route(
        self,
        query: str,
        request_id: Optional[str] = None,
        available_skills: Optional[List[str]] = None,
        baseline_skills: Optional[List[str]] = None,
        threshold: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        query = (query or "").strip()
        if not query:
            raise ValueError("query or user_message must be a non-empty string.")

        resolved_threshold = self.settings.threshold if threshold is None else float(threshold)
        if not 0.0 <= resolved_threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0.")

        resolved_top_k = self.settings.top_k if top_k is None else int(top_k)
        if resolved_top_k < 1:
            raise ValueError("top_k must be at least 1.")
        resolved_top_k = min(resolved_top_k, len(self.skill_names))

        available_skills = self._unique_skills(available_skills)
        allowed_set = None if available_skills is None else set(available_skills) & set(self.skill_names)
        unknown_available = [] if available_skills is None else [
            skill for skill in available_skills if skill not in self.skill_index
        ]

        started = time.perf_counter()
        with self._inference_lock:
            predictions = self.model.predict(
                query,
                self.skill_names,
                top_k=len(self.skill_names),
                threshold=0.0,
            )

        ranked = [
            {"skill_name": item["skill"], "score": item["score"]}
            for item in predictions
            if allowed_set is None or item["skill"] in allowed_set
        ]
        selected = [
            item for item in ranked if item["score"] >= resolved_threshold
        ][:resolved_top_k]
        selected_names = [item["skill_name"] for item in selected]

        shadow_comparison = None
        if baseline_skills is not None:
            baseline_names = self._unique_skills(baseline_skills) or []
            baseline_set = set(baseline_names)
            selected_set = set(selected_names)
            shadow_comparison = {
                "baseline_skills": baseline_names,
                "retained_skills": sorted(selected_set & baseline_set),
                "suggested_additions": sorted(selected_set - baseline_set),
                "suggested_removals": sorted(baseline_set - selected_set),
            }

        result = {
            "request_id": request_id,
            "selected_skills": selected,
            "selected_skill_names": selected_names,
            "threshold": resolved_threshold,
            "top_k": resolved_top_k,
            "mode": "recommendation",
            "available_skill_count": len(allowed_set) if allowed_set is not None else len(self.skill_names),
            "unknown_available_skills": unknown_available,
            "shadow_comparison": shadow_comparison,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
        self._write_audit_record(query, result)
        self._write_dashboard_event(result)
        return result

    def _write_audit_record(self, query: str, result: Dict[str, Any]) -> None:
        if self.settings.audit_log is None:
            return
        record = {
            "timestamp": time.time(),
            "request_id": result["request_id"],
            "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "selected_skill_names": result["selected_skill_names"],
            "threshold": result["threshold"],
            "top_k": result["top_k"],
            "unknown_available_skills": result["unknown_available_skills"],
            "shadow_comparison": result["shadow_comparison"],
            "latency_ms": result["latency_ms"],
        }
        self.settings.audit_log.parent.mkdir(parents=True, exist_ok=True)
        with self._audit_lock:
            with open(self.settings.audit_log, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _write_dashboard_event(self, result: Dict[str, Any]) -> None:
        if self.dashboard is None:
            return
        self.dashboard.append_event(
            {
                "timestamp": time.time(),
                "plugin_id": "sidecar-route",
                "request_id": result.get("request_id"),
                "ok": True,
                "selected_skill_names": result.get("selected_skill_names") or [],
                "shadow_comparison": result.get("shadow_comparison"),
                "latency_ms": result.get("latency_ms"),
                "active_model": str(self.settings.checkpoint),
            }
        )


def create_app(runtime: RouterRuntime):
    from fastapi import Body, FastAPI, HTTPException
    from fastapi.responses import FileResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(title="SkillRouter Sidecar", version="1.0.0")

    if WEBUI_DIR.exists():
        app.mount("/ui/assets", StaticFiles(directory=str(WEBUI_DIR)), name="skillrouter-ui-assets")

    @app.get("/", include_in_schema=False)
    def index():
        return RedirectResponse(url="/ui/")

    @app.get("/ui", include_in_schema=False)
    @app.get("/ui/", include_in_schema=False)
    def webui():
        path = WEBUI_DIR / "index.html"
        if not path.exists():
            raise HTTPException(status_code=404, detail="WebUI assets are not installed.")
        return FileResponse(path)

    @app.get("/healthz")
    def healthz():
        return runtime.info()

    @app.get("/v1/skills")
    def skills():
        return {"skills": runtime.skill_names, "count": len(runtime.skill_names)}

    @app.post("/v1/route")
    def route(payload: RouteRequest = Body(...)):
        try:
            policy = runtime.dashboard.policy() if runtime.dashboard is not None else {}
            if policy.get("routing_enabled") is False:
                return {
                    "request_id": payload.request_id,
                    "ok": True,
                    "selected_skills": [],
                    "selected_skill_names": [],
                    "threshold": policy.get("threshold", runtime.settings.threshold),
                    "top_k": policy.get("top_k", runtime.settings.top_k),
                    "mode": "paused",
                    "skipped": "routing_paused_by_dashboard",
                    "available_skill_count": len(payload.available_skills or runtime.skill_names),
                    "unknown_available_skills": [],
                    "shadow_comparison": None,
                    "latency_ms": 0.0,
                }
            threshold = policy.get("threshold") if policy.get("enforce_parameters") else payload.threshold
            top_k = policy.get("top_k") if policy.get("enforce_parameters") else payload.top_k
            return runtime.route(
                query=payload.query or payload.user_message or "",
                request_id=payload.request_id,
                available_skills=payload.available_skills,
                baseline_skills=payload.baseline_skills,
                threshold=threshold,
                top_k=top_k,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.get("/v1/dashboard/policy")
    def get_dashboard_policy():
        if runtime.dashboard is None:
            raise HTTPException(status_code=404, detail="Dashboard store is disabled.")
        return runtime.dashboard.policy()

    @app.put("/v1/dashboard/policy")
    def update_dashboard_policy(payload: Dict[str, Any] = Body(...)):
        if runtime.dashboard is None:
            raise HTTPException(status_code=404, detail="Dashboard store is disabled.")
        return runtime.dashboard.save_policy(payload)

    @app.post("/v1/dashboard/events")
    def ingest_dashboard_event(payload: Dict[str, Any] = Body(...)):
        if runtime.dashboard is None:
            raise HTTPException(status_code=404, detail="Dashboard store is disabled.")
        return {"ok": True, "event": runtime.dashboard.append_event(payload)}

    @app.get("/v1/dashboard/events")
    def dashboard_events(limit: int = 200):
        if runtime.dashboard is None:
            raise HTTPException(status_code=404, detail="Dashboard store is disabled.")
        return {"events": runtime.dashboard.events(limit)}

    @app.get("/v1/dashboard/summary")
    def dashboard_summary(limit: int = 1000):
        if runtime.dashboard is None:
            raise HTTPException(status_code=404, detail="Dashboard store is disabled.")
        return {
            "router": runtime.info(),
            "policy": runtime.dashboard.policy(),
            "metrics": runtime.dashboard.summary(limit),
        }

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the trained SkillRouter as an HTTP sidecar.")
    parser.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    parser.add_argument("--skill-index", default=str(DEFAULT_SKILL_INDEX))
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--allow-model-download", action="store_true")
    parser.add_argument("--audit-log", default=None)
    parser.add_argument("--dashboard-dir", default=str(DEFAULT_DASHBOARD_DIR))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8780)
    args = parser.parse_args()

    settings = RouterSettings(
        checkpoint=Path(args.checkpoint),
        skill_index=Path(args.skill_index),
        embedding_model=args.embedding_model,
        device=args.device,
        threshold=args.threshold,
        top_k=args.top_k,
        local_files_only=not args.allow_model_download,
        audit_log=Path(args.audit_log) if args.audit_log else None,
        dashboard_dir=Path(args.dashboard_dir) if args.dashboard_dir else None,
    )
    runtime = RouterRuntime(settings)

    import uvicorn

    uvicorn.run(create_app(runtime), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
