import time

from taskq.models import Job
from taskq.scheduler import promote_due
from taskq.service import enqueue_job
from taskq.worker import recover, work_once


def _get(session_factory, jid):
    with session_factory() as s:
        return s.get(Job, jid)


def test_successful_job(session_factory, queue):
    with session_factory() as s:
        job = enqueue_job(s, queue, "_echo", {"value": 42})
        jid = job.id
    with session_factory() as s:
        outcome = work_once(s, queue, "w1")
    assert outcome == "succeeded"
    row = _get(session_factory, jid)
    assert row.status == "succeeded"
    assert row.result == "42"
    assert queue.r.llen(queue.processing_key("w1")) == 0


def test_retry_then_dead(session_factory, queue, _register_test_tasks):
    _register_test_tasks["calls"] = 0
    _register_test_tasks["fail_until"] = 99  # never succeeds
    with session_factory() as s:
        job = enqueue_job(s, queue, "_flaky", {}, max_attempts=2)
        jid = job.id

    # attempt 1 -> retry (goes back to the scheduled set)
    with session_factory() as s:
        assert work_once(s, queue, "w1") == "retry"
    assert _get(session_factory, jid).status == "scheduled"

    # promote the scheduled retry back into the queue, then run the final attempt
    with session_factory() as s:
        promote_due(s, queue, now=time.time() + 10_000)
    with session_factory() as s:
        assert work_once(s, queue, "w1") == "dead"

    row = _get(session_factory, jid)
    assert row.status == "dead"
    assert row.attempts == 2
    assert queue.r.llen(queue.dead_key) == 1


def test_retry_then_success(session_factory, queue, _register_test_tasks):
    _register_test_tasks["calls"] = 0
    _register_test_tasks["fail_until"] = 1  # fail once, then succeed
    with session_factory() as s:
        job = enqueue_job(s, queue, "_flaky", {}, max_attempts=3)
        jid = job.id

    with session_factory() as s:
        assert work_once(s, queue, "w1") == "retry"
    with session_factory() as s:
        promote_due(s, queue, now=time.time() + 10_000)
    with session_factory() as s:
        assert work_once(s, queue, "w1") == "succeeded"

    assert _get(session_factory, jid).status == "succeeded"


def test_recover_requeues_running_jobs(session_factory, queue):
    with session_factory() as s:
        job = enqueue_job(s, queue, "_echo", {"value": 1})
        jid = job.id
    # simulate a worker that claimed + marked running, then crashed
    queue.claim("w1")
    with session_factory() as s:
        s.get(Job, jid).status = "running"
        s.commit()
    with session_factory() as s:
        recover(s, queue, "w1")
    assert _get(session_factory, jid).status == "queued"
    assert queue.claim("w2") == jid
