from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .disambiguation import run_disambiguation
from .errors import WorkerRuntimeError
from .providers import create_provider
from .research import revalidate_private_draft, run_confirmed_research


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the minimal architecture case-research worker.")
    parser.add_argument("--query", help="Project name or a short project brief, for example: Villa Savoye, Poissy.")
    parser.add_argument("--request", type=Path, help="Path to an existing generation-request JSON file.")
    parser.add_argument("--location-hint", default="")
    parser.add_argument("--architect-hint", default="")
    parser.add_argument("--year-hint", default="")
    parser.add_argument("--case-type-hint", default="")
    parser.add_argument("--job-id", default="")
    parser.add_argument("--output-root", type=Path, default=Path("tmp/worker-jobs"))
    parser.add_argument("--provider", choices=["openai", "deepseek", "fixture"], help="Override ARCHITECT_LLM_PROVIDER.")
    parser.add_argument("--confirm-job", default="", help="Continue an existing job after editor confirmation.")
    parser.add_argument("--validate-job", default="", help="Revalidate one existing private draft without another model call.")
    parser.add_argument("--candidate-id", default="", help="Candidate ID to confirm with --confirm-job.")
    parser.add_argument("--confirmed-by", default="local-cli", help="Editor user ID recorded for --confirm-job.")
    args = parser.parse_args(argv)

    confirmation_mode = bool(args.confirm_job)
    revalidation_mode = bool(args.validate_job)
    if confirmation_mode and revalidation_mode:
        parser.error("--confirm-job and --validate-job cannot be combined")
    if not confirmation_mode and not revalidation_mode and bool(args.query) == bool(args.request):
        parser.error("provide exactly one of --query or --request")
    if confirmation_mode and (args.query or args.request or args.job_id):
        parser.error("--confirm-job cannot be combined with --query, --request, or --job-id")
    if confirmation_mode and not args.candidate_id.strip():
        parser.error("--candidate-id is required with --confirm-job")
    if revalidation_mode and (args.query or args.request or args.job_id or args.candidate_id):
        parser.error("--validate-job cannot be combined with query, request, job-id, or candidate-id options")

    try:
        if revalidation_mode:
            output_path = revalidate_private_draft(jobs_root=args.output_root, job_id=args.validate_job)
        elif confirmation_mode:
            request = read_job_request(args.output_root, args.confirm_job)
            output_path = run_confirmed_research(
                request=request,
                jobs_root=args.output_root,
                provider=create_provider(args.provider),
                confirmation={
                    "job_id": args.confirm_job,
                    "candidate_id": args.candidate_id,
                    "confirmed_by": {"user_id": args.confirmed_by, "role": "editor"},
                    "confirmed_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                },
            )
        else:
            request = read_request(args) if args.request else make_request(args)
            output_path = run_disambiguation(
                request=request,
                jobs_root=args.output_root,
                provider=create_provider(args.provider),
            )
    except WorkerRuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"ERROR: worker filesystem error: {error}", file=sys.stderr)
        return 1

    print(output_path.resolve())
    return 0


def read_request(args: argparse.Namespace) -> dict[str, Any]:
    try:
        value = json.loads(args.request.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise WorkerRuntimeError(f"request JSON is invalid: {error.msg}") from error
    if not isinstance(value, dict):
        raise WorkerRuntimeError("request JSON must be an object.")
    return value


def read_job_request(jobs_root: Path, job_id: str) -> dict[str, Any]:
    path = jobs_root / job_id / "request.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise WorkerRuntimeError(f"job request was not found: {path}") from error
    except json.JSONDecodeError as error:
        raise WorkerRuntimeError(f"job request JSON is invalid: {error.msg}") from error
    if not isinstance(value, dict):
        raise WorkerRuntimeError("stored job request must be an object.")
    return value


def make_request(args: argparse.Namespace) -> dict[str, Any]:
    job_id = args.job_id.strip() or f"job_{uuid.uuid4().hex}"
    return {
        "job_id": job_id,
        "idempotency_key": f"local_{job_id}",
        "mode": "generate",
        "requested_by": {"user_id": "local-cli", "role": "editor"},
        "project": {
            "query": args.query,
            "architect_or_studio": args.architect_hint,
            "location_hint": args.location_hint,
            "year_hint": args.year_hint,
            "case_type_hint": args.case_type_hint,
        },
        "research_options": {
            "language": "zh-CN",
            "source_mode": "web",
            "allow_web_supplementation": True,
            "image_mode": "research_download",
            "public_image_default": "review_required",
        },
        "input_files": [],
        "requested_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
