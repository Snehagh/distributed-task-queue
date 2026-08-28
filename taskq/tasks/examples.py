"""Example job handlers. Add your own by decorating a function with @task("name").

A handler receives the job payload as keyword arguments and may return a
JSON-serialisable result (stored on the job record)."""
import time

from ..registry import task


@task("compute_fibonacci")
def compute_fibonacci(n=10):
    a, b = 0, 1
    for _ in range(int(n)):
        a, b = b, a + b
    return a


@task("send_welcome_email")
def send_welcome_email(email, name="there"):
    # Stubbed side effect; swap in a real mail client in your own build.
    print(f"[email] Hi {name}, welcome! -> {email}")
    return f"queued welcome email to {email}"


@task("slow_query")
def slow_query(seconds=2):
    time.sleep(float(seconds))
    return f"slept {seconds}s"


@task("always_fail")
def always_fail():
    # Demonstrates retries with exponential backoff, then the dead-letter queue.
    raise RuntimeError("this task always fails on purpose")
