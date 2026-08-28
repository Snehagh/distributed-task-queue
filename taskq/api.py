"""FastAPI surface: submit jobs, check status, list, retry, and see queue stats."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException

from . import tasks  # noqa: F401  (registers example handlers)
from .config import settings
from .db import SessionLocal, init_db, make_redis
from .models import Job
from .queue import RedisQueue
from .registry import is_registered, registered_tasks
from .schemas import EnqueueRequest, JobOut
from .service import enqueue_job

_redis = make_redis()
_queue = RedisQueue(_redis, namespace=settings.namespace)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="taskq", version="0.1.0", lifespan=lifespan)


def get_session():
    with SessionLocal() as session:
        yield session


def get_queue():
    return _queue


@app.get("/healthz")
def healthz():
    return {"ok": True, "tasks": registered_tasks()}


@app.post("/jobs", response_model=JobOut, status_code=201)
def create_job(req: EnqueueRequest, session=Depends(get_session), queue=Depends(get_queue)):
    if not is_registered(req.task):
        raise HTTPException(400, f"unknown task '{req.task}'. Known: {registered_tasks()}")
    try:
        job = enqueue_job(session, queue, req.task, req.payload,
                          req.priority, req.delay, req.max_attempts)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return JobOut(**job.to_dict())


@app.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, session=Depends(get_session)):
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return JobOut(**job.to_dict())


@app.get("/jobs", response_model=list[JobOut])
def list_jobs(status: str | None = None, limit: int = 50, session=Depends(get_session)):
    q = session.query(Job)
    if status:
        q = q.filter(Job.status == status)
    rows = q.order_by(Job.created_at.desc()).limit(min(limit, 200)).all()
    return [JobOut(**j.to_dict()) for j in rows]


@app.post("/jobs/{job_id}/retry", response_model=JobOut)
def retry_job(job_id: str, session=Depends(get_session), queue=Depends(get_queue)):
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    if job.status not in ("failed", "dead"):
        raise HTTPException(409, f"can only retry failed/dead jobs (status={job.status})")
    job.status = "queued"
    job.error = None
    session.commit()
    queue.enqueue(job.id, job.priority)
    return JobOut(**job.to_dict())


@app.get("/stats")
def stats(session=Depends(get_session), queue=Depends(get_queue)):
    counts = {}
    for (status,) in session.query(Job.status).all():
        counts[status] = counts.get(status, 0) + 1
    return {"by_status": counts, "queue_depths": queue.depths()}
