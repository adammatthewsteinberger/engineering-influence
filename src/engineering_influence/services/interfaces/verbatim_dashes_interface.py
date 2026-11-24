# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for VerbatimDashes."""

from abc import ABC

from engineering_influence.services.interfaces.dash_rewriter_interface import (
    DashRewriterInterface,
)


class VerbatimDashesInterface(DashRewriterInterface, ABC):
    """A dash rewriter that leaves a novel's dashes as written."""

    __slots__ = ()
