# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ContextPlan."""

from abc import ABC


class ContextPlanInterface(ABC):
    """Everything that could go into one drafting call, before it is fitted to a token budget."""

    __slots__ = ()
