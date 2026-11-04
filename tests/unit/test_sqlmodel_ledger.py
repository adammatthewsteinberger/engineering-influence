"""Durable ledger adapter tests."""

from engineering_influence.repositories import SqlModelLedger


def test_sqlmodel_ledger_round_trip_preserves_append_order() -> None:
    ledger = SqlModelLedger()
    ledger.append("pipeline.started", {"project_slug": "demo", "stage": "thesis"})
    ledger.append("phase.queued", {"project_slug": "demo", "stage": "thesis"})

    assert ledger.events() == [
        ("pipeline.started", {"project_slug": "demo", "stage": "thesis"}),
        ("phase.queued", {"project_slug": "demo", "stage": "thesis"}),
    ]
    ledger.close()
