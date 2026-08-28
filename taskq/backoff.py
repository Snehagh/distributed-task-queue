"""Pure retry-delay maths, kept dependency-free so it is trivial to unit test."""
from .config import settings


def backoff_seconds(attempt, base=None, factor=None, cap=None):
    """Delay before the next retry, given the attempt number that just failed (1-based).

    Exponential: base * factor ** (attempt - 1), capped at `cap`.
    """
    base = settings.backoff_base if base is None else base
    factor = settings.backoff_factor if factor is None else factor
    cap = settings.backoff_cap if cap is None else cap
    attempt = max(attempt, 1)
    delay = base * (factor ** (attempt - 1))
    return float(min(delay, cap))
