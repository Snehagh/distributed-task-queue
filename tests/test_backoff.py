from taskq.backoff import backoff_seconds


def test_backoff_is_exponential():
    assert backoff_seconds(1, base=2, factor=3, cap=1000) == 2
    assert backoff_seconds(2, base=2, factor=3, cap=1000) == 6
    assert backoff_seconds(3, base=2, factor=3, cap=1000) == 18


def test_backoff_respects_cap():
    assert backoff_seconds(10, base=2, factor=3, cap=50) == 50


def test_backoff_is_monotonic_until_cap():
    delays = [backoff_seconds(a, base=1, factor=2, cap=1e9) for a in range(1, 8)]
    assert delays == sorted(delays)
