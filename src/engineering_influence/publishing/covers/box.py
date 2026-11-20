# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Deprecated path: ``Box`` moved to ``engineering_influence.covers``."""

import warnings

from engineering_influence.covers import Box

warnings.warn(
    "engineering_influence.publishing.covers.box is deprecated and will be removed in the "
    "next minor release; import Box from engineering_influence.covers",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["Box"]
