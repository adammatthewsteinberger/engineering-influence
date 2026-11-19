# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Ordered pipeline stages."""

from enum import StrEnum


class PipelineStage(StrEnum):
    """The top-level stages a project may select."""

    THESIS = "thesis"
    BOOK = "book"
    NOVEL = "novel"
    SCREENPLAY = "screenplay"
    HUB = "hub"
    SPOKES = "spokes"
    DISTRIBUTION = "distribution"
    PUBLISH = "publish"
