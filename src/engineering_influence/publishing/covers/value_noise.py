# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Deprecated path: ``ValueNoise`` moved to ``engineering_influence.covers``."""

import warnings

from engineering_influence.covers import ValueNoise

warnings.warn(
    "engineering_influence.publishing.covers.value_noise is deprecated and will be removed in the "
    "next minor release; import ValueNoise from engineering_influence.covers",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ValueNoise"]
