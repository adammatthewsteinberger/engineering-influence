# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Deprecated path: ``FilmGrain`` moved to ``engineering_influence.covers``."""

import warnings

from engineering_influence.covers import FilmGrain

warnings.warn(
    "engineering_influence.publishing.covers.film_grain is deprecated and will be removed in the "
    "next minor release; import FilmGrain from engineering_influence.covers",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["FilmGrain"]
