# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Deprecated path: ``CoverPlugin`` moved to ``engineering_influence.covers``."""

import warnings

from engineering_influence.covers import CoverPlugin

warnings.warn(
    "engineering_influence.publishing.covers.cover_plugin is deprecated and will be removed in the "
    "next minor release; import CoverPlugin from engineering_influence.covers",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["CoverPlugin"]
