# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A webhook event to queue with a run's state change: its id, the receiver's URL, its name and its payload."""

from dataclasses import dataclass, field

from engineering_influence.models.interfaces.outbox_event_interface import OutboxEventInterface


@dataclass(frozen=True, slots=True)
class OutboxEvent(OutboxEventInterface):
    """`event_id` is the same on every retry of the event, so a receiver can ignore a repeat."""

    event_id: str
    url: str
    event_name: str
    payload: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("event id", self.event_id),
            ("url", self.url),
            ("event name", self.event_name),
        ):
            if not value.strip():
                raise ValueError(f"an outbox event needs a non-blank {name}")

    def record_key(self) -> str:
        """The event id."""
        return self.event_id
