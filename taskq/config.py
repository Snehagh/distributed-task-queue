"""Runtime configuration, read from environment variables with sensible defaults."""
import os


class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./taskq.db")
    namespace: str = os.getenv("TASKQ_NAMESPACE", "taskq")

    max_attempts: int = int(os.getenv("TASKQ_MAX_ATTEMPTS", "3"))
    # Retry delay = base * factor ** (attempt - 1), capped. Defaults: 2s, 6s, 18s, ...
    backoff_base: float = float(os.getenv("TASKQ_BACKOFF_BASE", "2"))
    backoff_factor: float = float(os.getenv("TASKQ_BACKOFF_FACTOR", "3"))
    backoff_cap: float = float(os.getenv("TASKQ_BACKOFF_CAP", "900"))

    poll_interval: float = float(os.getenv("TASKQ_POLL_INTERVAL", "1.0"))
    scheduler_interval: float = float(os.getenv("TASKQ_SCHEDULER_INTERVAL", "1.0"))


settings = Settings()

PRIORITIES = ("high", "default", "low")
