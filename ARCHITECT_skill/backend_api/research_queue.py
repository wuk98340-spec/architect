"""Durable, single-consumer research queue backed by the shared job volume."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from typing import Any, Callable


TaskRunner = Callable[[dict[str, Any]], None]


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_task(workspace: Path) -> dict[str, Any] | None:
    for name in ("research-task.json", "research-task.running.json"):
        path = workspace / name
        if path.exists():
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                return value
    return None


class ResearchQueue:
    """Persist work before returning so Cloud Run lifecycle events cannot lose it."""

    def __init__(self, *, jobs_root: Path, poll_seconds: float = 1.0) -> None:
        self.jobs_root = jobs_root
        self.poll_seconds = poll_seconds
        self.stop_event = Event()

    def enqueue(self, *, job_id: str, confirmation: dict[str, Any]) -> dict[str, Any]:
        workspace = self.jobs_root / job_id
        existing = read_task(workspace)
        if existing and existing.get("state") in {"queued", "running"}:
            return existing
        task = {
            "job_id": job_id,
            "state": "queued",
            "confirmation": confirmation,
            "queued_at": utc_now(),
        }
        _write_json(workspace / "research-task.json", task)
        return task

    def recover_interrupted_tasks(self) -> None:
        if not self.jobs_root.exists():
            return
        for workspace in self.jobs_root.iterdir():
            running = workspace / "research-task.running.json"
            if not workspace.is_dir() or not running.exists():
                continue
            task = read_task(workspace)
            if task is None:
                continue
            task["state"] = "queued"
            task["recovered_at"] = utc_now()
            _write_json(workspace / "research-task.json", task)
            running.unlink(missing_ok=True)

    def claim_next(self) -> tuple[Path, dict[str, Any]] | None:
        if not self.jobs_root.exists():
            return None
        for workspace in sorted(path for path in self.jobs_root.iterdir() if path.is_dir()):
            queued = workspace / "research-task.json"
            running = workspace / "research-task.running.json"
            if not queued.exists():
                continue
            try:
                queued.replace(running)
            except FileNotFoundError:
                continue
            task = read_task(workspace)
            if task is None:
                continue
            task["state"] = "running"
            task["started_at"] = utc_now()
            _write_json(running, task)
            return workspace, task
        return None

    def finish(self, *, workspace: Path, task: dict[str, Any], error: Exception | None = None) -> None:
        task["state"] = "failed" if error else "completed"
        task["finished_at"] = utc_now()
        if error:
            task["error"] = str(error)
        _write_json(workspace / "research-task.json", task)
        (workspace / "research-task.running.json").unlink(missing_ok=True)

    def process_one(self, runner: TaskRunner, *, on_settled: Callable[[Path], None] | None = None) -> bool:
        claimed = self.claim_next()
        if claimed is None:
            return False
        workspace, task = claimed
        try:
            runner(task)
        except Exception as error:
            self.finish(workspace=workspace, task=task, error=error)
        else:
            self.finish(workspace=workspace, task=task)
        if on_settled:
            on_settled(workspace)
        return True

    def run_forever(self, runner: TaskRunner) -> None:
        self.recover_interrupted_tasks()
        while not self.stop_event.is_set():
            if not self.process_one(runner):
                self.stop_event.wait(self.poll_seconds)

    def stop(self) -> None:
        self.stop_event.set()
