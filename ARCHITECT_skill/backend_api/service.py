"""Read-only job projections and request construction for the HTTP API."""

from __future__ import annotations

import json
import os
import shutil
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from worker_runtime.errors import OutputValidationError


JOB_ID_PATTERN = re.compile(r"^job_[a-zA-Z0-9_-]{1,120}$")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_case_packages_root() -> Path:
    return Path(os.environ.get("ARCHITECT_CASE_PACKAGES_ROOT", Path(__file__).resolve().parents[2] / "case-packages"))


def require_job_id(job_id: str) -> str:
    if not JOB_ID_PATTERN.fullmatch(job_id):
        raise OutputValidationError("job_id must start with 'job_' and contain only letters, digits, '_' or '-'.")
    return job_id


def read_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FileNotFoundError(f"{label} was not found.") from error
    except json.JSONDecodeError as error:
        raise OutputValidationError(f"{label} is invalid JSON: {error.msg}") from error
    if not isinstance(value, dict):
        raise OutputValidationError(f"{label} must be a JSON object.")
    return value


def latest_event(workspace: Path) -> dict[str, Any] | None:
    path = workspace / "events.jsonl"
    if not path.exists():
        return None
    last: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            candidate = json.loads(line)
            if isinstance(candidate, dict):
                last = candidate
    return last


def public_status(worker_state: str | None) -> str:
    # Keep the worker's persisted vocabulary untouched while providing the API
    # contract requested by the web flow.
    return {"waiting_for_confirmation": "awaiting_confirmation", "generating": "researching"}.get(
        worker_state or "", worker_state or "unknown"
    )


def queue_view(workspace: Path) -> dict[str, Any] | None:
    for name in ("research-task.running.json", "research-task.json"):
        path = workspace / name
        if path.exists():
            return read_object(path, label="research task")
    return None


def job_view(*, jobs_root: Path, job_id: str) -> dict[str, Any]:
    require_job_id(job_id)
    workspace = jobs_root / job_id
    if not workspace.is_dir():
        raise FileNotFoundError("job was not found.")
    request = read_object(workspace / "request.json", label="job request")
    event = latest_event(workspace)
    artifacts = workspace / "artifacts"
    view: dict[str, Any] = {
        "job_id": job_id,
        "status": public_status(str(event.get("state")) if event else None),
        "worker_state": event.get("state") if event else None,
        "request": request,
        "last_event": event,
    }
    for key, filename in (("disambiguation", "disambiguation.json"), ("validation", "validation.json")):
        path = artifacts / filename
        if path.exists():
            view[key] = read_object(path, label=key)
    confirmation = workspace / "confirmation.json"
    if confirmation.exists():
        view["confirmation"] = read_object(confirmation, label="confirmation")
    saved = workspace / "saved.json"
    if saved.exists():
        view["saved"] = read_object(saved, label="saved result")
        view["status"] = "saved"
    task = queue_view(workspace)
    if task:
        view["queue"] = {key: value for key, value in task.items() if key != "confirmation"}
        if task.get("state") == "failed" and view["status"] != "saved":
            view["status"] = "failed"
            view["worker_state"] = "failed"
            view["error"] = {"message": str(task.get("error", "research worker failed"))}
    return view


def build_request(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query", "")).strip()
    if not query:
        raise OutputValidationError("query is required and must not be empty.")
    supplied_job_id = str(payload.get("job_id", "")).strip()
    job_id = require_job_id(supplied_job_id) if supplied_job_id else f"job_{uuid.uuid4().hex}"
    requested_by = payload.get("requested_by") or {}
    if not isinstance(requested_by, dict):
        raise OutputValidationError("requested_by must be an object.")
    user_id = str(requested_by.get("user_id", "api")).strip() or "api"
    return {
        "job_id": job_id,
        "idempotency_key": str(payload.get("idempotency_key", f"api_{job_id}")),
        "mode": "generate",
        "requested_by": {"user_id": user_id, "role": str(requested_by.get("role", "editor"))},
        "project": {
            "query": query,
            "architect_or_studio": str(payload.get("architect_hint", "")),
            "location_hint": str(payload.get("location_hint", "")),
            "year_hint": str(payload.get("year_hint", "")),
            "case_type_hint": str(payload.get("case_type_hint", "")),
        },
        "research_options": payload.get("research_options") if isinstance(payload.get("research_options"), dict) else {
            "language": "zh-CN", "source_mode": "web", "allow_web_supplementation": True,
            "image_mode": "research_download", "public_image_default": "review_required",
        },
        "input_files": [],
        "requested_at": utc_now(),
    }


def result_view(*, jobs_root: Path, job_id: str) -> dict[str, Any]:
    view = job_view(jobs_root=jobs_root, job_id=job_id)
    package_root = jobs_root / job_id / "artifacts" / "package"
    packages = [path for path in package_root.iterdir() if path.is_dir()] if package_root.exists() else []
    if len(packages) != 1:
        return {
            "job_id": job_id,
            "status": view["status"],
            "worker_state": view["worker_state"],
            "processing": view["status"] == "researching",
            "last_event": view.get("last_event"),
            "error": view.get("error"),
        }
    package = packages[0]
    case_md = package / "case.md"
    return {
        "job_id": job_id,
        "status": view["status"],
        "case_json": read_object(package / "case.json", label="case.json"),
        "case_md": case_md.read_text(encoding="utf-8"),
        "validation": view.get("validation"),
    }


def save_result_to_library(
    *,
    jobs_root: Path,
    case_packages_root: Path,
    job_id: str,
    rebuild_site: Callable[[], None],
) -> dict[str, Any]:
    """Persist a validated private draft only after the user explicitly saves it."""
    view = job_view(jobs_root=jobs_root, job_id=job_id)
    existing_save = view.get("saved")
    if isinstance(existing_save, dict):
        return existing_save
    validation = view.get("validation")
    if not isinstance(validation, dict) or not validation.get("passed_for_review"):
        raise LookupError("only a generated result that passed validation can be saved.")

    package_root = jobs_root / job_id / "artifacts" / "package"
    packages = [path for path in package_root.iterdir() if path.is_dir()] if package_root.exists() else []
    if len(packages) != 1:
        raise LookupError("job result is not available yet.")
    source = packages[0]
    destination = case_packages_root / source.name
    if destination.exists():
        raise FileExistsError(f"case package '{source.name}' already exists; existing cases are never overwritten.")

    case_packages_root.mkdir(parents=True, exist_ok=True)
    staging = case_packages_root / f".{source.name}.saving-{uuid.uuid4().hex}"
    try:
        shutil.copytree(source, staging)
        staging.replace(destination)
        rebuild_site()
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        # A failed site rebuild should not create an apparently saved case.
        if destination.exists():
            shutil.rmtree(destination)
        raise

    saved = {
        "job_id": job_id,
        "package_slug": source.name,
        "package_path": str(destination),
        "saved_at": utc_now(),
        "message": "User saved the validated case to the library.",
    }
    (jobs_root / job_id / "saved.json").write_text(
        json.dumps(saved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return saved
