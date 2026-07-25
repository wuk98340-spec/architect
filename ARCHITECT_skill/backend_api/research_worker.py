"""Cloud Run worker process for the durable ARCHITECT research queue."""

from __future__ import annotations

from threading import Thread
from typing import Any

from worker_runtime.providers import create_provider
from worker_runtime.research import run_confirmed_research

from .app import default_jobs_root, serve
from .research_queue import ResearchQueue
from .service import read_object, require_job_id


def run_task(queue: ResearchQueue, task: dict[str, Any]) -> None:
    job_id = require_job_id(str(task["job_id"]))
    workspace = queue.jobs_root / job_id
    confirmation = task.get("confirmation")
    if not isinstance(confirmation, dict):
        raise ValueError("queued research task is missing its confirmation.")
    run_confirmed_research(
        request=read_object(workspace / "request.json", label="job request"),
        jobs_root=queue.jobs_root,
        provider=create_provider(),
        confirmation=confirmation,
    )


def main() -> None:
    queue = ResearchQueue(jobs_root=default_jobs_root())
    worker = Thread(target=queue.run_forever, args=(lambda task: run_task(queue, task),), daemon=False)
    worker.start()
    try:
        # Cloud Run requires a listener on PORT. This internal-only service uses
        # the existing health endpoint while the non-daemon thread owns queue work.
        serve()
    finally:
        queue.stop()
        worker.join()


if __name__ == "__main__":
    main()
