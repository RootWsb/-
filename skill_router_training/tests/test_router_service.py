import json
import tempfile
import unittest
from pathlib import Path

from skill_router_training.service.app import RouterRuntime, RouterSettings, create_app


class FakeModel:
    def predict(self, query, skill_names, top_k, threshold):
        return [
            {"skill": "alpha", "score": 0.99},
            {"skill": "beta", "score": 0.82},
            {"skill": "gamma", "score": 0.61},
        ]


class RouterRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        checkpoint = root / "checkpoint"
        checkpoint.mkdir()
        (checkpoint / "config.json").write_text(
            json.dumps(
                {
                    "num_skills": 3,
                    "embedding_model": "missing-model",
                    "hidden_dim": 256,
                    "dropout": 0.1,
                }
            ),
            encoding="utf-8",
        )
        index = root / "skill_index.json"
        index.write_text(json.dumps({"alpha": 0, "beta": 1, "gamma": 2}), encoding="utf-8")
        self.audit_log = root / "audit.jsonl"
        self.runtime = RouterRuntime(
            RouterSettings(
                checkpoint=checkpoint,
                skill_index=index,
                device="cpu",
                top_k=2,
                threshold=0.5,
                audit_log=self.audit_log,
                dashboard_dir=root / "dashboard",
            ),
            model=FakeModel(),
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_filters_to_agent_available_skills_before_selecting_top_k(self):
        result = self.runtime.route(
            "build a plugin",
            available_skills=["beta", "gamma", "not-trained-yet"],
        )

        self.assertEqual(result["selected_skill_names"], ["beta", "gamma"])
        self.assertEqual(result["unknown_available_skills"], ["not-trained-yet"])
        self.assertEqual(result["available_skill_count"], 2)

    def test_returns_shadow_comparison_without_replacing_baseline(self):
        result = self.runtime.route(
            "build a plugin",
            baseline_skills=["alpha", "gamma"],
            top_k=2,
        )

        self.assertEqual(result["selected_skill_names"], ["alpha", "beta"])
        self.assertEqual(
            result["shadow_comparison"],
            {
                "baseline_skills": ["alpha", "gamma"],
                "retained_skills": ["alpha"],
                "suggested_additions": ["beta"],
                "suggested_removals": ["gamma"],
            },
        )

    def test_audit_log_does_not_persist_raw_query(self):
        raw_query = "private user request text"
        self.runtime.route(raw_query, request_id="req-1")

        record = json.loads(self.audit_log.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(record["request_id"], "req-1")
        self.assertIn("query_sha256", record)
        self.assertNotIn(raw_query, self.audit_log.read_text(encoding="utf-8"))

    def test_app_exposes_sidecar_endpoints(self):
        app = create_app(self.runtime)
        paths = {route.path for route in app.routes}

        self.assertIn("/healthz", paths)
        self.assertIn("/v1/skills", paths)
        self.assertIn("/v1/route", paths)
        self.assertIn("/v1/dashboard/events", paths)
        self.assertIn("/v1/dashboard/summary", paths)

    def test_dashboard_event_ingest_is_privacy_safe(self):
        raw_query = "do not persist this private request"
        record = self.runtime.dashboard.append_event(
            {
                "request_id": "req-2",
                "ok": True,
                "user_message": raw_query,
                "selected_skill_names": ["alpha", "beta"],
                "shadow_comparison": {"baseline_skills": ["alpha", "gamma"]},
            }
        )

        self.assertEqual(record["selected_skill_names"], ["alpha", "beta"])
        self.assertNotIn("user_message", record)
        self.assertNotIn(raw_query, self.runtime.dashboard.events_path.read_text(encoding="utf-8"))

    def test_route_calls_are_mirrored_to_dashboard_events(self):
        self.runtime.route(
            "build a plugin",
            request_id="req-route",
            baseline_skills=["alpha", "gamma"],
        )

        summary = self.runtime.dashboard.summary()
        self.assertEqual(summary["event_count"], 1)
        self.assertEqual(summary["comparable_count"], 1)
        self.assertEqual(summary["avg_selected_before"], 2)
        self.assertEqual(summary["avg_selected_after"], 2)

    def test_dashboard_policy_can_pause_and_override_route(self):
        from fastapi.testclient import TestClient

        app = create_app(self.runtime)
        client = TestClient(app)

        paused = client.put("/v1/dashboard/policy", json={"routing_enabled": False})
        self.assertEqual(paused.status_code, 200)
        paused_route = client.post("/v1/route", json={"user_message": "build a plugin"})
        self.assertEqual(paused_route.status_code, 200)
        self.assertEqual(paused_route.json()["selected_skill_names"], [])
        self.assertEqual(paused_route.json()["skipped"], "routing_paused_by_dashboard")

        override = client.put(
            "/v1/dashboard/policy",
            json={"routing_enabled": True, "enforce_parameters": True, "threshold": 0.9, "top_k": 1},
        )
        self.assertEqual(override.status_code, 200)
        routed = client.post("/v1/route", json={"user_message": "build a plugin", "threshold": 0.1, "top_k": 3})
        self.assertEqual(routed.status_code, 200)
        self.assertEqual(routed.json()["selected_skill_names"], ["alpha"])
        self.assertEqual(routed.json()["threshold"], 0.9)
        self.assertEqual(routed.json()["top_k"], 1)


if __name__ == "__main__":
    unittest.main()
