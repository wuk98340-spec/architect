import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from backend_api.app import create_server
from worker_runtime.providers import FixtureProvider


class BackendApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.library = self.root / "case-packages"
        self.rebuild_calls = 0
        def rebuild_site():
            self.rebuild_calls += 1
        self.server = create_server(
            jobs_root=self.root,
            case_packages_root=self.library,
            provider_factory=FixtureProvider,
            rebuild_site=rebuild_site,
            port=0,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def request(self, method, path, body=None):
        connection = HTTPConnection(*self.server.server_address)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
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

    def test_local_frontend_cors_preflight_is_allowed(self):
        connection = HTTPConnection(*self.server.server_address)
        connection.request("OPTIONS", "/api/jobs", headers={"Origin": "http://127.0.0.1:8765"})
        response = connection.getresponse()
        self.assertEqual(response.status, 204)
        self.assertEqual(response.getheader("Access-Control-Allow-Origin"), "*")
        response.read()
        connection.close()

    def test_confirm_delegates_to_worker_and_result_reads_private_artifacts(self):
        created = self.create_job()
        job_id = created["job_id"]
        package = self.root / job_id / "artifacts" / "package" / "villa-savoye"
        package.mkdir(parents=True)
        (package / "case.json").write_text('{"project_name": "Villa Savoye"}', encoding="utf-8")
        (package / "case.md").write_text("# Villa Savoye\n", encoding="utf-8")
        (self.root / job_id / "artifacts" / "validation.json").write_text('{"passed_for_review": true}', encoding="utf-8")

        # Replace the costly research stage only in this HTTP-boundary test;
        # worker_runtime has its own end-to-end confirmation coverage.
        import backend_api.app as app
        original = app.run_confirmed_research
        try:
            def complete_worker(**kwargs):
                workspace = self.root / kwargs["confirmation"]["job_id"]
                (workspace / "confirmation.json").write_text(json.dumps(kwargs["confirmation"]), encoding="utf-8")
                with (workspace / "events.jsonl").open("a", encoding="utf-8") as events:
                    events.write(json.dumps({"state": "awaiting_review", "type": "stage_completed"}) + "\n")
                return package

            app.run_confirmed_research = complete_worker
            status, confirmed = self.request("POST", f"/api/jobs/{job_id}/confirm", {"candidate_id": "villa-savoye-1931"})
        finally:
            app.run_confirmed_research = original
        self.assertEqual(status, 200)
        self.assertEqual(confirmed["status"], "awaiting_review")
        status, result = self.request("GET", f"/api/jobs/{job_id}/result")
        self.assertEqual(status, 200)
        self.assertEqual(result["case_json"]["project_name"], "Villa Savoye")
        self.assertTrue(result["validation"]["passed_for_review"])

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
