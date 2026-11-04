# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Phase-runner port."""

from abc import ABC, abstractmethod


class RunnerPort(ABC):
    """Execute one phase with an already-loaded runner or skill."""

    @abstractmethod
    async def run(self, phase: str, context: dict[str, object]) -> str:
        """Return the phase artifact content."""
