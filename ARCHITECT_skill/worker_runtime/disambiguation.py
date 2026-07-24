"""First worker stage: generation request -> LLM -> validated disambiguation artifact."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from .errors import OutputValidationError
from .providers import LLMProvider


RUNTIME_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = RUNTIME_ROOT.parent / "skills" / "architectural-case-study"
TEMPLATE_ROOT = SKILL_ROOT / "worker-templates"
SCHEMA_PATH = RUNTIME_ROOT / "schemas" / "disambiguation-result.schema.json"


def run_disambiguation(*, request: dict[str, Any], jobs_root: Path, provider: LLMProvider) -> Path:
    validate_generation_request(request)
    job_id = str(request["job_id"])
    workspace = jobs_root / job_id
    artifact_dir = workspace / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    write_json(workspace / "request.json", request)
    append_event(workspace, job_id, "disambiguating", "stage_started", "开始项目消歧。")

    try:
        schema = read_json(SCHEMA_PATH)
        instructions = build_instructions()
        result = provider.disambiguate(instructions=instructions, request=request, schema=schema)
        validate_disambiguation_result(result, expected_job_id=job_id, schema=schema)
        result["created_at"] = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        output_path = artifact_dir / "disambiguation.json"
        write_json(output_path, result)
        # A high-confidence model result speeds up review, but never bypasses
        # the human confirmation gate before research or draft creation begins.
        append_event(
            workspace,
            job_id,
            "waiting_for_confirmation",
            "stage_completed",
            "项目消歧结果已通过 JSON schema 校验，等待编辑确认候选。",
        )
        return output_path
    except Exception as error:
        append_event(workspace, job_id, "failed", "stage_failed", str(error))
        raise


def build_instructions() -> str:
    base = (TEMPLATE_ROOT / "worker-instructions.md").read_text(encoding="utf-8")
    stage = (TEMPLATE_ROOT / "disambiguation-instructions.md").read_text(encoding="utf-8")
    return f"{base}\n\n{stage}"


def validate_generation_request(request: dict[str, Any]) -> None:
    required = {"job_id", "idempotency_key", "mode", "requested_by", "project", "research_options", "requested_at"}
    missing = sorted(required - request.keys())
    if missing:
        raise OutputValidationError(f"generation request is missing required fields: {', '.join(missing)}")
    if request.get("mode") != "generate":
        raise OutputValidationError("minimal runtime supports only mode=generate.")
    if not str(request.get("job_id", "")).strip():
        raise OutputValidationError("generation request job_id must not be empty.")
    if not str((request.get("project") or {}).get("query", "")).strip():
        raise OutputValidationError("generation request project.query must not be empty.")


def validate_disambiguation_result(result: dict[str, Any], *, expected_job_id: str, schema: dict[str, Any]) -> None:
    if result.get("job_id") != expected_job_id:
        raise OutputValidationError("disambiguation result job_id does not match the request.")
    try:
        Draft202012Validator(schema).validate(result)
    except ValidationError as error:
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise OutputValidationError(f"disambiguation result failed JSON schema at {path}: {error.message}") from error


def append_event(workspace: Path, job_id: str, state: str, event_type: str, message: str) -> None:
    event = {
        "event_id": f"evt_{time.time_ns()}",
        "job_id": job_id,
        "attempt": 1,
        "state": state,
        "type": event_type,
        "message": message,
        "details": {},
        "occurred_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    with (workspace / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OutputValidationError(f"JSON object expected in {path}.")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
