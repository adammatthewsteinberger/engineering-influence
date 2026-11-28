# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Something that happens in the story, and where it falls in the story's own time."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.story_event_interface import StoryEventInterface
from engineering_influence.models.story_text import StoryText


@dataclass(frozen=True, slots=True)
class StoryEvent(StoryEventInterface):
    """One dated event.

    ``when`` is a position in the story's own time (a day number, a year, a step): only its order matters, so two
    events with the same ``when`` happen together. ``label`` is the words a chapter uses when it mentions the event.
    """

    MAX_LABEL: ClassVar[int] = 120
    MAX_WHEN: ClassVar[int] = 1_000_000

    when: int
    label: str

    def __post_init__(self) -> None:
        """Validate the event's time and label when it is built."""
        if type(self.when) is not int or not 0 <= self.when <= self.MAX_WHEN:
            raise ValueError(f"an event's time is a whole number from 0 to {self.MAX_WHEN:,}")
        StoryText.line("an event's label", self.label, self.MAX_LABEL)
