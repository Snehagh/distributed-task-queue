"""Engine/session helpers. SQLite is used for local tests, PostgreSQL in production."""
import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import settings
from .models import Base


def make_engine(url=None):
    url = url or settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db(target_engine=None):
    Base.metadata.create_all(target_engine or engine)


def make_redis(url=None):
    # decode_responses=True so we work with str job-ids, not bytes.
    return redis.Redis.from_url(url or settings.redis_url, decode_responses=True)
