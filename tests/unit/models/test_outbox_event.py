# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""OutboxEvent: an event needs an id, a receiver and a name, none of them blank."""

import pytest

from engineering_influence.models.outbox_event import OutboxEvent


@pytest.mark.parametrize(
    ("event_id", "url", "name"), [(" ", "https://a", "x"), ("e", "", "x"), ("e", "https://a", " ")]
)
def test_a_blank_field_is_refused(event_id: str, url: str, name: str) -> None:
    with pytest.raises(ValueError, match="non-blank"):
        OutboxEvent(event_id, url, name)


def test_the_record_key_is_the_event_id() -> None:
    assert OutboxEvent("evt-1", "https://a", "x").record_key() == "evt-1"
