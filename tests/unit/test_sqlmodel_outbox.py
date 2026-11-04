"""Outbox persistence tests."""

from engineering_influence.repositories import SqlModelOutbox


def test_outbox_is_idempotent_and_tracks_delivery() -> None:
    outbox = SqlModelOutbox()
    outbox.enqueue("evt-1", "https://receiver.test", "pipeline.started", {"slug": "demo"})
    outbox.enqueue("evt-1", "https://receiver.test", "pipeline.started", {"slug": "demo"})

    assert outbox.pending() == [
        ("evt-1", "https://receiver.test", "pipeline.started", {"slug": "demo"}, 0)
    ]

    outbox.mark_delivered("evt-1")
    assert outbox.pending() == []
    outbox.close()


def test_failures_are_counted_and_dead_events_stop_being_pending() -> None:
    outbox = SqlModelOutbox()
    outbox.enqueue("evt-1", "https://a.test", "x", {})

    assert outbox.mark_failed("evt-1") == 1
    assert outbox.mark_failed("evt-1") == 2
    assert outbox.pending()[0][4] == 2

    outbox.mark_dead("evt-1")

    assert outbox.pending() == []
    outbox.close()
