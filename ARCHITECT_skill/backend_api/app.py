"""Minimal threaded JSON HTTP API that delegates all work to worker_runtime."""

from __future__ import annotations

import json
import mimetypes
import os
import subprocess
import sys
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from worker_runtime.disambiguation import run_disambiguation
from worker_runtime.errors import WorkerRuntimeError
from worker_runtime.providers import LLMProvider, create_provider
from worker_runtime.research import confirm_research_job

from .service import (
    build_request,
    default_case_packages_root,
    job_view,
    read_object,
    require_job_id,
    result_view,
    save_result_to_library,
)
from .research_queue import ResearchQueue


ProviderFactory = Callable[[], LLMProvider]

DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:8765",
    "http://localhost:8765",
)


def cors_origins() -> frozenset[str]:
    """Read the browser origins allowed to call the public API.

    CloudBase Run injects environment variables at deploy time, which keeps
    the production static-hosting domain out of source code.  Empty entries
    are ignored so a trailing comma is harmless.
    """
    configured = os.environ.get("ARCHITECT_CORS_ORIGINS", "")
    values = configured.split(",") if configured else DEFAULT_CORS_ORIGINS
    return frozenset(value.strip() for value in values if value.strip())


def default_jobs_root() -> Path:
    return Path(os.environ.get("ARCHITECT_JOBS_ROOT", "tmp/worker-jobs"))


def default_static_root() -> Path:
    """Return the generated site directory served alongside the API."""
    workspace_root = Path(__file__).resolve().parents[2]
    return Path(os.environ.get("ARCHITECT_STATIC_ROOT", workspace_root / "architecture-case-site" / "public"))


def rebuild_static_site() -> None:
    workspace_root = Path(__file__).resolve().parents[2]
    site_root = workspace_root / "architecture-case-site"
    completed = subprocess.run(
        [sys.executable, str(site_root / "scripts" / "build_site.py")],
        cwd=site_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[:600]
        raise RuntimeError(f"case was not saved because the site rebuild failed: {detail}")


def create_server(
    *,
    jobs_root: Path | None = None,
    case_packages_root: Path | None = None,
    static_root: Path | None = None,
    provider_factory: ProviderFactory | None = None,
    rebuild_site: Callable[[], None] | None = None,
    research_queue: ResearchQueue | None = None,
    port: int | None = None,
) -> ThreadingHTTPServer:
    root = (jobs_root or default_jobs_root()).resolve()
    library_root = (case_packages_root or default_case_packages_root()).resolve()
    site_root = (static_root or default_static_root()).resolve()
    make_provider = provider_factory or create_provider
    build_site = rebuild_site or rebuild_static_site
    allowed_cors_origins = cors_origins()
    queue = research_queue or ResearchQueue(jobs_root=root)

    class Handler(BaseHTTPRequestHandler):
        server_version = "ARCHITECTBackend/0.1"

        def log_message(self, format: str, *args: object) -> None:
            return  # The host process can add its own request logging later.

        def do_GET(self) -> None:  # noqa: N802
            try:
                if self._try_serve_private_asset():
                    return
                if self.path.split("?", 1)[0] != "/healthz" and not self.path.split("?", 1)[0].startswith("/api/"):
                    self._serve_static_asset()
                    return
            except FileNotFoundError as error:
                self._error(HTTPStatus.NOT_FOUND, str(error))
                return
            except WorkerRuntimeError as error:
                self._error(HTTPStatus.UNPROCESSABLE_ENTITY, str(error))
                return
            self._dispatch()

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch()

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self._cors_headers()
            self.end_headers()

        def _dispatch(self) -> None:
            self._response_status = HTTPStatus.OK
            try:
                payload = self._route()
                self._json(self._response_status, payload)
            except FileNotFoundError as error:
                self._error(HTTPStatus.NOT_FOUND, str(error))
            except LookupError as error:
                self._error(HTTPStatus.CONFLICT, str(error))
            except FileExistsError as error:
                self._error(HTTPStatus.CONFLICT, str(error))
            except (WorkerRuntimeError, ValueError, json.JSONDecodeError) as error:
                self._error(HTTPStatus.UNPROCESSABLE_ENTITY, str(error))
            except Exception:
                self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")

        def _route(self) -> dict[str, Any]:
            parts = [part for part in self.path.split("?", 1)[0].split("/") if part]
            if self.command == "GET" and parts == ["healthz"]:
                return {"status": "ok"}
            if self.command == "POST" and parts == ["api", "jobs"]:
                request = build_request(self._body_object())
                run_disambiguation(request=request, jobs_root=root, provider=make_provider())
                return job_view(jobs_root=root, job_id=request["job_id"])
            if parts[:2] != ["api", "jobs"] or len(parts) not in {3, 4}:
                raise FileNotFoundError("route was not found.")
            job_id = require_job_id(parts[2])
            if self.command == "GET" and len(parts) == 3:
                return job_view(jobs_root=root, job_id=job_id)
            if self.command == "POST" and len(parts) == 4 and parts[3] == "confirm":
                return self._confirm(job_id)
            if self.command == "POST" and len(parts) == 4 and parts[3] == "save":
                return {"job_id": job_id, "saved": save_result_to_library(
                    jobs_root=root, case_packages_root=library_root, job_id=job_id, rebuild_site=build_site
                )}
            if self.command == "GET" and len(parts) == 4 and parts[3] == "result":
                return result_view(jobs_root=root, job_id=job_id)
            raise FileNotFoundError("route was not found.")

        def _serve_static_asset(self) -> None:
            """Serve generated public files so the frontend and API share one origin."""
            request_path = self.path.split("?", 1)[0]
            relative = Path("index.html") if request_path in {"", "/"} else Path(*[part for part in request_path.split("/") if part])
            if relative.is_absolute() or ".." in relative.parts:
                raise FileNotFoundError("static asset was not found.")
            target = (site_root / relative).resolve()
            if not target.is_file() or site_root not in target.parents:
                raise FileNotFoundError("static asset was not found.")
            body = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _try_serve_private_asset(self) -> bool:
            parts = [part for part in self.path.split("?", 1)[0].split("/") if part]
            if len(parts) < 6 or parts[:2] != ["api", "jobs"] or parts[3] != "assets":
                return False
            job_id = require_job_id(parts[2])
            relative = Path(*parts[4:])
            if relative.is_absolute() or ".." in relative.parts:
                raise FileNotFoundError("asset was not found.")
            package_root = root / job_id / "artifacts" / "package"
            packages = [path for path in package_root.iterdir() if path.is_dir()] if package_root.exists() else []
            if len(packages) != 1:
                raise FileNotFoundError("asset was not found.")
            target = (packages[0] / relative).resolve()
            if not target.is_file() or packages[0].resolve() not in target.parents:
                raise FileNotFoundError("asset was not found.")
            body = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self._cors_headers()
            self.end_headers()
            self.wfile.write(body)
            return True

        def _confirm(self, job_id: str) -> dict[str, Any]:
            payload = self._body_object()
            candidate_id = str(payload.get("candidate_id", "")).strip()
            if not candidate_id:
                raise ValueError("candidate_id is required and must not be empty.")
            request = read_object(root / job_id / "request.json", label="job request")
            confirmed_by = payload.get("confirmed_by") or {}
            if not isinstance(confirmed_by, dict):
                raise ValueError("confirmed_by must be an object.")
            confirmation = {
                "job_id": job_id, "candidate_id": candidate_id,
                "confirmed_by": {"user_id": str(confirmed_by.get("user_id", "api")).strip() or "api", "role": str(confirmed_by.get("role", "editor"))},
                "confirmed_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            }
            confirm_research_job(
                request=request, jobs_root=root,
                confirmation=confirmation,
            )
            queue.enqueue(job_id=job_id, confirmation=confirmation)
            self._response_status = HTTPStatus.ACCEPTED
            return job_view(jobs_root=root, job_id=job_id)

        def _body_object(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError("request body must be a JSON object.")
            value = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("request body must be a JSON object.")
            return value

        def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._cors_headers()
            self.end_headers()
            self.wfile.write(body)

        def _cors_headers(self) -> None:
            origin = self.headers.get("Origin", "").strip()
            if origin not in allowed_cors_origins:
                return
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Vary", "Origin")

        def _error(self, status: HTTPStatus, message: str) -> None:
            self._json(status, {"error": {"code": status.name.lower(), "message": message}})

    host = os.environ.get("ARCHITECT_API_HOST", "127.0.0.1")
    resolved_port = port if port is not None else int(os.environ.get("PORT", os.environ.get("ARCHITECT_API_PORT", "8000")))
    return ThreadingHTTPServer((host, resolved_port), Handler)


def serve() -> None:
    server = create_server()
    host, port = server.server_address
    print(f"ARCHITECT Backend API listening on http://{host}:{port}")
    server.serve_forever()
