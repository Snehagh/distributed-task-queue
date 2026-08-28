import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from taskq import api
from taskq.models import Base
from taskq.queue import RedisQueue


@pytest.fixture
def client():
    engine = create_engine("sqlite://", future=True, poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False,
                                  expire_on_commit=False, future=True)
    test_queue = RedisQueue(fakeredis.FakeStrictRedis(decode_responses=True), namespace="apitest")

    def _get_session():
        with TestingSession() as s:
            yield s

    api.app.dependency_overrides[api.get_session] = _get_session
    api.app.dependency_overrides[api.get_queue] = lambda: test_queue
    with TestClient(api.app) as c:
        yield c, test_queue
    api.app.dependency_overrides.clear()


def test_health(client):
    c, _ = client
    r = c.get("/healthz")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_create_and_fetch_job(client):
    c, q = client
    r = c.post("/jobs", json={"task": "compute_fibonacci", "payload": {"n": 10}})
    assert r.status_code == 201
    jid = r.json()["id"]
    assert r.json()["status"] == "queued"
    assert q.claim("w1") == jid  # pointer really landed in Redis

    r2 = c.get(f"/jobs/{jid}")
    assert r2.status_code == 200 and r2.json()["task"] == "compute_fibonacci"


def test_unknown_task_rejected(client):
    c, _ = client
    r = c.post("/jobs", json={"task": "does_not_exist"})
    assert r.status_code == 400


def test_scheduled_job_not_immediately_queued(client):
    c, q = client
    r = c.post("/jobs", json={"task": "compute_fibonacci", "delay": 60})
    assert r.json()["status"] == "scheduled"
    assert q.claim("w1") is None
    assert q.r.zcard(q.scheduled_key) == 1
