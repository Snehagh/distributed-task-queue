"""Pydantic request/response models for the API."""
from typing import Any

from pydantic import BaseModel, Field


class EnqueueRequest(BaseModel):
    task: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: str = "default"
    delay: float | None = None       # seconds from now; omit to run immediately
    max_attempts: int | None = None


class JobOut(BaseModel):
    id: str
    task: str
    priority: str
    status: str
    attempts: int
    max_attempts: int
    result: Any = None
    error: str | None = None
    scheduled_for: float | None = None
