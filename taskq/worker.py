"""Worker: claim a job, run its handler, then succeed / retry / dead-letter it."""
import json
import os
import time
import uuid

from . import tasks  # noqa: F401  (registers example handlers)
from .backoff import backoff_seconds
from .config import settings
from .db import SessionLocal, init_db, make_redis
from .models import Job
from .queue import RedisQueue
from .registry import get_handler


def run_job(session, job):
    """Execute one job. Commits state transitions. Returns the outcome string."""
    job.status = "running"
    job.attempts += 1
    session.commit()

    handler = get_handler(job.task_name)
    payload = json.loads(job.payload or "{}")
    try:
        result = handler(**payload) if isinstance(payload, dict) else handler(payload)
        job.status = "succeeded"
        job.result = json.dumps(result) if result is not None else None
        job.error = None
        session.commit()
        return "succeeded"
    except Exception as exc:  # noqa: BLE001 - we deliberately capture handler errors
        job.error = f"{type(exc).__name__}: {exc}"
        if job.attempts >= job.max_attempts:
            job.status = "dead"
            session.commit()
            return "dead"
        job.status = "scheduled"
        job.scheduled_for = time.time() + backoff_seconds(job.attempts)
        session.commit()
        return "retry"


def work_once(session, queue, worker_id):
    """Process a single job if one is available. Returns outcome or None."""
    job_id = queue.claim(worker_id)
    if job_id is None:
        return None

    job = session.get(Job, job_id)
    if job is None:
        queue.ack(worker_id, job_id)  # orphan pointer, drop it
        return None

    outcome = run_job(session, job)
    if outcome == "retry":
        queue.schedule(job_id, job.scheduled_for)
        queue.ack(worker_id, job_id)
    elif outcome == "dead":
        queue.to_dead(worker_id, job_id)
    else:  # succeeded
        queue.ack(worker_id, job_id)
    return outcome


def recover(session, queue, worker_id):
    """On startup, rescue jobs left behind by a previous crash."""
    def priority_lookup(job_id):
        job = session.get(Job, job_id)
        return job.priority if job else "default"

    queue.recover_processing(worker_id, priority_lookup)

    # Jobs stuck 'running' (worker died before ack) get requeued.
    stuck = session.query(Job).filter(Job.status == "running").all()
    for job in stuck:
        job.status = "queued"
        session.commit()
        queue.enqueue(job.id, job.priority)


def main():  # pragma: no cover - process entrypoint
    init_db()
    queue = RedisQueue(make_redis(), namespace=settings.namespace)
    worker_id = os.getenv("WORKER_ID", f"worker-{uuid.uuid4().hex[:8]}")
    print(f"[worker] starting as {worker_id}")

    with SessionLocal() as session:
        recover(session, queue, worker_id)

    while True:
        with SessionLocal() as session:
            outcome = work_once(session, queue, worker_id)
        if outcome is None:
            time.sleep(settings.poll_interval)
        else:
            print(f"[worker] {worker_id} -> {outcome}")


if __name__ == "__main__":  # pragma: no cover
    main()
