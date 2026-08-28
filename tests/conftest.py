import fakeredis
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from taskq.models import Base
from taskq.queue import RedisQueue
from taskq.registry import task


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite://", future=True, poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@pytest.fixture
def session(session_factory):
    with session_factory() as s:
        yield s


@pytest.fixture
def queue():
    client = fakeredis.FakeStrictRedis(decode_responses=True)
    return RedisQueue(client, namespace="test")


@pytest.fixture(scope="session", autouse=True)
def _register_test_tasks():
    # A handler we can flip between failing and succeeding across attempts.
    state = {"fail_until": 0, "calls": 0}

    @task("_flaky")
    def _flaky():
        state["calls"] += 1
        if state["calls"] <= state["fail_until"]:
            raise RuntimeError(f"boom on call {state['calls']}")
        return "ok"

    @task("_echo")
    def _echo(value=None):
        return value

    _flaky.state = state  # type: ignore[attr-defined]
    return state
