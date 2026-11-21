# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Whether a model can take a call right now."""

from enum import StrEnum


class ModelAvailability(StrEnum):
    """A model is usable, or it is blocked for a reason that decides what the run does next."""

    AVAILABLE = "available"
    WINDOW_EXHAUSTED = "window_exhausted"
    CREDITS_EXHAUSTED = "credits_exhausted"
    AUTHENTICATION_FAILED = "authentication_failed"
