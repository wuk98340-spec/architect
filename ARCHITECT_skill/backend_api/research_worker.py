"""Cloud Run worker process for the durable ARCHITECT research queue."""

from __future__ import annotations

import os
from threading import Thread
from typing import Any

from worker_runtime.providers import create_provider
from worker_runtime.research import run_confirmed_research

from .app import default_jobs_root, serve
from .research_queue import ResearchQueue
from .service import read_object, require_job_id
from .cos_storage import current_storage_mirror, storage_failure_message


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
    try:
        cos_mirror = current_storage_mirror()
    except Exception as error:
        # Keep the process observable and make readiness report the durable
        # storage failure. A crash loop hides a bad credential rotation and
        # makes recovery harder once the credentials have been corrected.
        os.environ["ARCHITECT_STORAGE_UNAVAILABLE"] = storage_failure_message(error)
        cos_mirror = None

    def consume() -> None:
        queue.recover_interrupted_tasks()
        while not queue.stop_event.is_set():
            if cos_mirror:
                cos_mirror.hydrate_all_jobs(jobs_root=queue.jobs_root)
            processed = queue.process_one(
                lambda task: run_task(queue, task),
                on_settled=(
                    (lambda workspace: cos_mirror.persist_job(jobs_root=queue.jobs_root, job_id=workspace.name))
                    if cos_mirror
                    else None
                ),
            )
            if not processed:
                queue.stop_event.wait(queue.poll_seconds)

    worker = Thread(target=consume, daemon=False)
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
