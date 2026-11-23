# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one rule for a short text that came out of a model and describes a story."""

from engineering_influence.models.interfaces.story_text_interface import StoryTextInterface


class StoryText(StoryTextInterface):
    """A name, a place or an event is one line of printable text with a length limit.

    Everything in a story bible came out of a model, so it is held to what can be shown on one line and
    searched for in a chapter: no line breaks, no control characters, nothing padded.
    """

    __slots__ = ()

    @staticmethod
    def line(label: str, text: str, limit: int) -> None:
        """Raise a ValueError naming ``label`` when ``text`` is not one printable line of at most ``limit`` characters."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{label} needs text")
        if len(text) > limit:
            raise ValueError(f"{label} is longer than {limit} characters")
        if text != text.strip() or not text.isprintable():
            raise ValueError(f"{label} is one line of printable text")
