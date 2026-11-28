# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The facts of a novel that every chapter has to agree with."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.story_bible_interface import StoryBibleInterface
from engineering_influence.models.story_character import StoryCharacter
from engineering_influence.models.story_event import StoryEvent
from engineering_influence.models.story_text import StoryText


@dataclass(frozen=True, slots=True)
class StoryBible(StoryBibleInterface):
    """The premise plus the names, places and dated events a continuity check compares a chapter against.

    It is bounded (``MAX_*``) so a model cannot make a later prompt or a check unbounded. No two characters
    share a name or an alias, and a place is not also a character's name, because the checker could not say which
    a near-miss spelling was meant for. ``span_years`` is how long the story runs, so a character who is 30 at the
    opening may be written as 31 by the end of a one-year story and not as 40.
    """

    MAX_PREMISE: ClassVar[int] = 2_000
    MAX_CHARACTERS: ClassVar[int] = 60
    MAX_PLACES: ClassVar[int] = 60
    MAX_EVENTS: ClassVar[int] = 100
    MAX_PLACE: ClassVar[int] = 80
    MAX_SPAN: ClassVar[int] = 200

    premise: str
    characters: tuple[StoryCharacter, ...] = ()
    places: tuple[str, ...] = ()
    timeline: tuple[StoryEvent, ...] = ()
    span_years: int = 0

    def __post_init__(self) -> None:
        """Validate the bible's premise, names, places and events when it is built."""
        StoryText.line("the premise", self.premise, self.MAX_PREMISE)
        self._check_characters()
        self._check_places()
        self._check_timeline()
        if type(self.span_years) is not int or not 0 <= self.span_years <= self.MAX_SPAN:
            raise ValueError(f"the span is a whole number of years from 0 to {self.MAX_SPAN}")

    def _check_characters(self) -> None:
        if not isinstance(self.characters, tuple) or len(self.characters) > self.MAX_CHARACTERS:
            raise ValueError(f"a story bible has at most {self.MAX_CHARACTERS} characters")
        if any(not isinstance(item, StoryCharacter) for item in self.characters):
            raise TypeError("a bible's characters are story characters")
        if len(set(self.names())) != len(self.names()):
            raise ValueError("character names must be distinct")

    def _check_places(self) -> None:
        if not isinstance(self.places, tuple) or len(self.places) > self.MAX_PLACES:
            raise ValueError(f"a story bible has at most {self.MAX_PLACES} places")
        for place in self.places:
            StoryText.line("a place", place, self.MAX_PLACE)
        if len({place.casefold() for place in self.places}) != len(self.places):
            raise ValueError("places must be distinct")
        if {place.casefold() for place in self.places} & set(self.names()):
            raise ValueError("a place cannot share a name with a character")

    def _check_timeline(self) -> None:
        if not isinstance(self.timeline, tuple) or len(self.timeline) > self.MAX_EVENTS:
            raise ValueError(f"a story bible has at most {self.MAX_EVENTS} events")
        if any(not isinstance(item, StoryEvent) for item in self.timeline):
            raise TypeError("a bible's timeline is story events")
        labels = [event.label.casefold() for event in self.timeline]
        if len(set(labels)) != len(labels):
            raise ValueError("event labels must be distinct")
        times = [event.when for event in self.timeline]
        if times != sorted(times):
            raise ValueError("the timeline is listed in the order things happen")

    def names(self) -> tuple[str, ...]:
        """Every written form of every character, folded to one case, for telling characters apart."""
        return tuple(form.casefold() for item in self.characters for form in item.forms())
