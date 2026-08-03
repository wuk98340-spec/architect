import json
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

from backend_api.app import cors_origins, create_server
from backend_api.research_queue import ResearchQueue
from worker_runtime.providers import FixtureProvider


class BackendApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.library = self.root / "case-packages"
        self.queue = ResearchQueue(jobs_root=self.root)
        self.rebuild_calls = 0
        def rebuild_site():
            self.rebuild_calls += 1
        self.server = create_server(
            jobs_root=self.root,
            case_packages_root=self.library,
            provider_factory=FixtureProvider,
            rebuild_site=rebuild_site,
            research_queue=self.queue,
            port=0,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = HTTPConnection(*self.server.server_address)
        request_headers = dict(headers or {})
        if body is not None:
            request_headers.setdefault("Content-Type", "application/json")
        connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=request_headers)
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        connection.close()
        return response.status, payload

    def create_job(self):
        status, payload = self.request("POST", "/api/jobs", {"query": "Villa Savoye, Le Corbusier, Poissy"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "awaiting_confirmation")
        return payload

    def test_create_and_get_job_exposes_confirmation_candidates(self):
        created = self.create_job()
        status, payload = self.request("GET", f"/api/jobs/{created['job_id']}")
        self.assertEqual(status, 200)
        self.assertEqual(payload["worker_state"], "waiting_for_confirmation")
        self.assertEqual(payload["disambiguation"]["candidates"][0]["candidate_id"], "villa-savoye-1931")

    def test_invalid_payload_and_missing_job_have_useful_http_errors(self):
        status, payload = self.request("POST", "/api/jobs", {"query": " "})
        self.assertEqual(status, 422)
        self.assertIn("query is required", payload["error"]["message"])
        status, _ = self.request("GET", "/api/jobs/job_does_not_exist")
        self.assertEqual(status, 404)

    def test_liveness_and_storage_readiness_are_separate(self):
        status, payload = self.request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})
        status, payload = self.request("GET", "/readyz")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ready", "storage": "ready"})

    def test_readiness_is_safely_degraded_when_cos_is_unavailable(self):
        with patch.dict("os.environ", {"ARCHITECT_COS_STORAGE_UNAVAILABLE": "COS authentication failed"}):
            server = create_server(
                jobs_root=self.root,
                case_packages_root=self.library,
                provider_factory=FixtureProvider,
                rebuild_site=lambda: None,
                port=0,
            )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = HTTPConnection(*server.server_address)
            connection.request("GET", "/healthz")
            health = connection.getresponse()
            self.assertEqual(health.status, 200)
            health.read()
            connection.close()

            connection = HTTPConnection(*server.server_address)
            connection.request("GET", "/readyz")
            readiness = connection.getresponse()
            self.assertEqual(readiness.status, 503)
            self.assertEqual(
                json.loads(readiness.read().decode("utf-8")),
                {"status": "not_ready", "storage": "unavailable"},
            )
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_local_frontend_cors_preflight_is_allowed(self):
        connection = HTTPConnection(*self.server.server_address)
        connection.request("OPTIONS", "/api/jobs", headers={"Origin": "http://127.0.0.1:8765"})
        response = connection.getresponse()
        self.assertEqual(response.status, 204)
        self.assertEqual(response.getheader("Access-Control-Allow-Origin"), "http://127.0.0.1:8765")
        response.read()
        connection.close()

    def test_cors_origins_reads_the_cloudbase_setting_and_rejects_other_sites(self):
        cloudbase_site = "https://architect-dev-d3g2rg2jfcda0906a-1457963611.tcloudbaseapp.com"
        with patch.dict("os.environ", {"ARCHITECT_CORS_ORIGINS": f" http://localhost:8765, {cloudbase_site}, "}):
            self.assertEqual(cors_origins(), frozenset({"http://localhost:8765", cloudbase_site}))
            server = create_server(
                jobs_root=self.root,
                case_packages_root=self.library,
                provider_factory=FixtureProvider,
                rebuild_site=lambda: None,
                port=0,
            )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = HTTPConnection(*server.server_address)
            connection.request("OPTIONS", "/api/jobs", headers={"Origin": cloudbase_site})
            response = connection.getresponse()
            self.assertEqual(response.status, 204)
            self.assertEqual(response.getheader("Access-Control-Allow-Origin"), cloudbase_site)
            response.read()
            connection.close()

            connection = HTTPConnection(*server.server_address)
            connection.request(
                "POST",
                "/api/jobs",
                body=json.dumps({"query": "Villa Savoye"}),
                headers={"Content-Type": "application/json", "Origin": cloudbase_site},
            )
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader("Access-Control-Allow-Origin"), cloudbase_site)
            response.read()
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

        connection = HTTPConnection(*self.server.server_address)
        connection.request("OPTIONS", "/api/jobs", headers={"Origin": "https://untrusted.example"})
        response = connection.getresponse()
        self.assertEqual(response.status, 204)
        self.assertIsNone(response.getheader("Access-Control-Allow-Origin"))
        response.read()
        connection.close()

    def test_confirm_queues_research_and_result_reports_processing_then_completion(self):
        created = self.create_job()
        job_id = created["job_id"]
        started = time.monotonic()
        status, confirmed = self.request("POST", f"/api/jobs/{job_id}/confirm", {"candidate_id": "villa-savoye-1931"})
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(status, 202)
        self.assertEqual(confirmed["status"], "researching")
        self.assertEqual(confirmed["worker_state"], "generating")
        self.assertEqual(confirmed["queue"]["state"], "queued")

        status, processing = self.request("GET", f"/api/jobs/{job_id}/result")
        self.assertEqual(status, 200)
        self.assertTrue(processing["processing"])
        self.assertEqual(processing["status"], "researching")

        def complete_task(task):
            package = self.root / task["job_id"] / "artifacts" / "package" / "villa-savoye"
            package.mkdir(parents=True)
            (package / "case.json").write_text('{"project_name": "Villa Savoye"}', encoding="utf-8")
            (package / "case.md").write_text("# Villa Savoye\n", encoding="utf-8")
            (self.root / task["job_id"] / "artifacts" / "validation.json").write_text('{"passed_for_review": true}', encoding="utf-8")
            with (self.root / task["job_id"] / "events.jsonl").open("a", encoding="utf-8") as events:
                events.write(json.dumps({"state": "awaiting_review", "type": "stage_completed"}) + "\n")

        self.assertTrue(self.queue.process_one(complete_task))
        status, result = self.request("GET", f"/api/jobs/{job_id}/result")
        self.assertEqual(status, 200)
        self.assertEqual(result["case_json"]["project_name"], "Villa Savoye")
        self.assertTrue(result["validation"]["passed_for_review"])

    def test_failed_background_task_is_explicit_in_result_view(self):
        created = self.create_job()
        job_id = created["job_id"]
        status, _ = self.request("POST", f"/api/jobs/{job_id}/confirm", {"candidate_id": "villa-savoye-1931"})
        self.assertEqual(status, 202)

        self.assertTrue(self.queue.process_one(lambda task: (_ for _ in ()).throw(RuntimeError("provider unavailable"))))
        status, result = self.request("GET", f"/api/jobs/{job_id}/result")
        self.assertEqual(status, 200)
        self.assertFalse(result["processing"])
        self.assertEqual(result["status"], "failed")
        self.assertIn("provider unavailable", result["error"]["message"])

    def test_queue_recovers_a_task_interrupted_by_worker_restart(self):
        job_id = "job_interrupted"
        (self.root / job_id).mkdir()
        self.queue.enqueue(job_id=job_id, confirmation={"job_id": job_id, "candidate_id": "candidate-1"})
        self.assertIsNotNone(self.queue.claim_next())
        restarted_queue = ResearchQueue(jobs_root=self.root)
        restarted_queue.recover_interrupted_tasks()
        task = json.loads((self.root / job_id / "research-task.json").read_text(encoding="utf-8"))
        self.assertEqual(task["state"], "queued")
        self.assertFalse((self.root / job_id / "research-task.running.json").exists())

    def test_user_can_save_a_validated_private_result_to_the_case_library(self):
        created = self.create_job()
        job_id = created["job_id"]
        package = self.root / job_id / "artifacts" / "package" / "villa-savoye"
        package.mkdir(parents=True)
        (package / "case.json").write_text('{"project_name": "Villa Savoye"}', encoding="utf-8")
        (package / "case.md").write_text("# Villa Savoye\n", encoding="utf-8")
        (self.root / job_id / "artifacts" / "validation.json").write_text('{"passed_for_review": true}', encoding="utf-8")

        status, payload = self.request("POST", f"/api/jobs/{job_id}/save", {})

        self.assertEqual(status, 200)
        self.assertEqual(payload["saved"]["package_slug"], "villa-savoye")
        self.assertTrue((self.library / "villa-savoye" / "case.json").exists())
        self.assertEqual(self.rebuild_calls, 1)
        status, job = self.request("GET", f"/api/jobs/{job_id}")
        self.assertEqual(status, 200)
        self.assertEqual(job["status"], "saved")

    def test_preview_can_read_a_private_job_image(self):
        created = self.create_job()
        job_id = created["job_id"]
        image = self.root / job_id / "artifacts" / "package" / "villa-savoye" / "images" / "hero.png"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"png-test")
        connection = HTTPConnection(*self.server.server_address)
        connection.request("GET", f"/api/jobs/{job_id}/assets/images/hero.png")
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.read(), b"png-test")
        connection.close()


if __name__ == "__main__":
    unittest.main()
