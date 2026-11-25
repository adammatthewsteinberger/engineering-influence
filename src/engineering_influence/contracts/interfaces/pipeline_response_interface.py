# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PipelineResponse."""

from abc import ABC


class PipelineResponseInterface(ABC):
    """Stable response shared by API, MCP, CLI, and SDK adapters."""

    __slots__ = ()
