"""The Redis-backed queue.

Design (built on raw Redis primitives, no queue library):
  * One LIST per priority: taskq:q:high / taskq:q:default / taskq:q:low.
    Producers LPUSH (left); workers pop from the right, giving FIFO per queue.
  * Reliable claim: RPOPLPUSH moves a job id straight into a per-worker
    "processing" list in one atomic step, so a job is never lost if the worker
    dies mid-run. On restart the worker requeues whatever is left there.
  * Delayed / retry jobs live in a sorted set (taskq:scheduled) scored by their
    run-at unix time. The scheduler promotes due ids into the priority queues.
  * Exhausted jobs go to a dead-letter list (taskq:dead).

Semantics are at-least-once: a crash between "finish work" and "ack" can cause a
re-run, so handlers should be idempotent.
"""
from .config import PRIORITIES


class RedisQueue:
    def __init__(self, client, namespace="taskq"):
        self.r = client
        self.ns = namespace

    # --- key helpers ---
    def qkey(self, priority):
        return f"{self.ns}:q:{priority}"

    @property
    def scheduled_key(self):
        return f"{self.ns}:scheduled"

    @property
    def dead_key(self):
        return f"{self.ns}:dead"

    def processing_key(self, worker_id):
        return f"{self.ns}:processing:{worker_id}"

    # --- producing ---
    def enqueue(self, job_id, priority="default"):
        self.r.lpush(self.qkey(priority), job_id)

    def schedule(self, job_id, run_at):
        self.r.zadd(self.scheduled_key, {job_id: run_at})

    # --- scheduler ---
    def due_jobs(self, now):
        return self.r.zrangebyscore(self.scheduled_key, 0, now)

    def pop_scheduled(self, job_id):
        """Atomically remove a scheduled id; returns True if we were the remover."""
        return self.r.zrem(self.scheduled_key, job_id) == 1

    # --- consuming ---
    def claim(self, worker_id):
        """Pull the next id in priority order into the worker's processing list."""
        for priority in PRIORITIES:
            job_id = self.r.rpoplpush(self.qkey(priority), self.processing_key(worker_id))
            if job_id is not None:
                return job_id
        return None

    def ack(self, worker_id, job_id):
        self.r.lrem(self.processing_key(worker_id), 1, job_id)

    def to_dead(self, worker_id, job_id):
        self.ack(worker_id, job_id)
        self.r.lpush(self.dead_key, job_id)

    def recover_processing(self, worker_id, priority_lookup):
        """Requeue anything left in this worker's processing list after a crash."""
        recovered = []
        while True:
            job_id = self.r.rpop(self.processing_key(worker_id))
            if job_id is None:
                break
            self.enqueue(job_id, priority_lookup(job_id))
            recovered.append(job_id)
        return recovered

    # --- introspection (for /stats) ---
    def depths(self):
        d = {p: self.r.llen(self.qkey(p)) for p in PRIORITIES}
        d["scheduled"] = self.r.zcard(self.scheduled_key)
        d["dead"] = self.r.llen(self.dead_key)
        return d
