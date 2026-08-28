"""Scheduler: promotes due jobs from the scheduled sorted-set into priority queues."""
import time

from .config import settings
from .db import SessionLocal, init_db, make_redis
from .models import Job
from .queue import RedisQueue


def promote_due(session, queue, now=None):
    """Move every job whose run-at has passed into its priority queue. Returns ids moved."""
    now = now if now is not None else time.time()
    moved = []
    for job_id in queue.due_jobs(now):
        if not queue.pop_scheduled(job_id):
            continue  # another scheduler instance grabbed it first
        job = session.get(Job, job_id)
        priority = job.priority if job else "default"
        if job:
            job.status = "queued"
            session.commit()
        queue.enqueue(job_id, priority)
        moved.append(job_id)
    return moved


def main():  # pragma: no cover - process entrypoint
    init_db()
    queue = RedisQueue(make_redis(), namespace=settings.namespace)
    print("[scheduler] starting")
    while True:
        with SessionLocal() as session:
            moved = promote_due(session, queue)
        if moved:
            print(f"[scheduler] promoted {len(moved)} job(s)")
        time.sleep(settings.scheduler_interval)


if __name__ == "__main__":  # pragma: no cover
    main()
