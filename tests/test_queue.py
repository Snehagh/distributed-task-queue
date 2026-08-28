import time


def test_fifo_within_a_queue(queue):
    for jid in ("a", "b", "c"):
        queue.enqueue(jid, "default")
    got = [queue.claim("w1") for _ in range(3)]
    assert got == ["a", "b", "c"]


def test_priority_order(queue):
    queue.enqueue("low1", "low")
    queue.enqueue("hi1", "high")
    queue.enqueue("def1", "default")
    assert queue.claim("w1") == "hi1"
    assert queue.claim("w1") == "def1"
    assert queue.claim("w1") == "low1"


def test_claim_moves_to_processing_and_ack_clears(queue):
    queue.enqueue("j1")
    queue.claim("w1")
    assert queue.r.llen(queue.processing_key("w1")) == 1
    queue.ack("w1", "j1")
    assert queue.r.llen(queue.processing_key("w1")) == 0


def test_recover_requeues_orphans(queue):
    queue.enqueue("j1", "high")
    queue.claim("w1")            # now in w1's processing list
    # simulate crash: never acked. A fresh start recovers it.
    recovered = queue.recover_processing("w1", priority_lookup=lambda _id: "high")
    assert recovered == ["j1"]
    assert queue.claim("w2") == "j1"


def test_dead_letter(queue):
    queue.enqueue("j1")
    queue.claim("w1")
    queue.to_dead("w1", "j1")
    assert queue.r.llen(queue.dead_key) == 1
    assert queue.r.llen(queue.processing_key("w1")) == 0


def test_scheduled_promotion(queue):
    now = time.time()
    queue.schedule("future", now + 1000)
    queue.schedule("due", now - 5)
    due = queue.due_jobs(now)
    assert "due" in due and "future" not in due
    assert queue.pop_scheduled("due") is True
    assert queue.pop_scheduled("due") is False  # already removed
