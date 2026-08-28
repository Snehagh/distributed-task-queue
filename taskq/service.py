"""Enqueue logic shared by the API and by tests."""
import json
import time
import uuid

from .config import PRIORITIES, settings
from .models import Job


def enqueue_job(session, queue, task, payload=None, priority="default",
                delay=None, max_attempts=None):
    if priority not in PRIORITIES:
        raise ValueError(f"priority must be one of {PRIORITIES}")

    job = Job(
        id=str(uuid.uuid4()),
        task_name=task,
        payload=json.dumps(payload or {}),
        priority=priority,
        max_attempts=max_attempts or settings.max_attempts,
        attempts=0,
    )

    if delay and delay > 0:
        job.status = "scheduled"
        job.scheduled_for = time.time() + delay
    else:
        job.status = "queued"

    session.add(job)
    session.commit()

    if job.status == "scheduled":
        queue.schedule(job.id, job.scheduled_for)
    else:
        queue.enqueue(job.id, job.priority)
    return job
