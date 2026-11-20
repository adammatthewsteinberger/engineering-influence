# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Deprecated path: ``Compositing`` moved to ``engineering_influence.covers``."""

import warnings

from engineering_influence.covers import Compositing

warnings.warn(
    "engineering_influence.publishing.covers.compositing is deprecated and will be removed in the "
    "next minor release; import Compositing from engineering_influence.covers",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["Compositing"]
