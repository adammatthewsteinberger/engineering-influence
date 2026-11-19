# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Deprecated path: ``ProjectLayout`` moved to ``engineering_influence.models.publishing``."""

import warnings

from engineering_influence.models.publishing.project_layout import ProjectLayout

warnings.warn(
    "engineering_influence.publishing.project_layout is deprecated and will be removed in the "
    "next minor release; import ProjectLayout from "
    "engineering_influence.models.publishing.project_layout",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ProjectLayout"]
