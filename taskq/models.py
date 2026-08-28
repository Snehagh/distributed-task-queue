"""SQLAlchemy models. The database is the source of truth for a job's state;
Redis only holds lightweight pointers (job ids) for fast dispatch."""
import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# Job lifecycle:
#   queued    -> in a Redis priority queue, waiting for a worker
#   scheduled -> waiting in the Redis sorted-set until its run-at time (delay/retry)
#   running   -> claimed by a worker, handler executing
#   succeeded -> handler returned
#   failed    -> handler raised but retries remain (transient state before re-schedule)
#   dead      -> retries exhausted; parked in the dead-letter queue
class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_name: Mapped[str] = mapped_column(String(128), index=True)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    priority: Mapped[str] = mapped_column(String(16), default="default", index=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_for: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "task": self.task_name,
            "payload": json.loads(self.payload or "{}"),
            "priority": self.priority,
            "status": self.status,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "result": json.loads(self.result) if self.result else None,
            "error": self.error,
            "scheduled_for": self.scheduled_for,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
