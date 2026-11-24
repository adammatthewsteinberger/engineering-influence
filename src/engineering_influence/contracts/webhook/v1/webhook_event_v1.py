# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Version 1 of a webhook event: the body of every delivery, and the catalogue of what can be delivered."""

from collections.abc import Mapping
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from engineering_influence.contracts.webhook.v1.interfaces.webhook_event_v1_interface import (
    WebhookEventV1Interface,
)


class WebhookEventV1(WebhookEventV1Interface, BaseModel):
    """``{"schema_version": 1, "id": ..., "type": ..., "data": {...}}``, sent as canonical JSON (sorted keys, no spaces).

    ``id`` is the event's id and is the same on every retry of it, so a receiver can ignore a repeat. ``type`` names the
    event and ``data`` is its payload. ``TYPES`` is the catalogue: the events a stack's services record, each with the keys
    its ``data`` carries. A key may be added to an event's ``data`` and a type may be added to the catalogue without a new
    schema version (a receiver must ignore what it does not know); removing or renaming either needs version 2, which runs
    beside this one for at least a minor release (docs/COMPATIBILITY.md).

    **Nothing delivers these yet:** the stack's worker records the events and the delivery and signing exist, but no service
    sends them (docs/CONFIGURATION.md). The catalogue and the envelope are frozen so that a receiver written now keeps working.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    TYPES: ClassVar[Mapping[str, tuple[str, ...]]] = {
        "pipeline.started": ("project_slug", "remaining_stages", "stage"),
        "phase.completed": ("artifact_id", "job_id", "phase", "project_slug"),
        "gate.awaiting": ("gate", "job_id", "phase", "project_slug"),
        "pipeline.completed": ("project_slug",),
    }
    HEADERS: ClassVar[tuple[str, ...]] = (
        "Content-Type",
        "X-Engineering-Influence-Event",
        "X-Engineering-Influence-Event-Id",
        "X-Engineering-Influence-Signature",
        "X-Engineering-Influence-Timestamp",
    )

    schema_version: Literal[1] = 1
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    data: dict[str, Any]
