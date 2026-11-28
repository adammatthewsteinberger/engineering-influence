# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How long, and how much memory and disk, an external build tool may use."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.tool_limits_interface import ToolLimitsInterface


@dataclass(frozen=True, slots=True)
class ToolLimits(ToolLimitsInterface):
    """The ceilings one tool run must stay under, or be stopped.

    ``max_memory_bytes`` is resident memory summed over the tool and everything it started,
    not address space: a JVM reserves far more than it touches. ``max_disk_bytes`` is the total
    size of the directory the tool writes into.
    """

    timeout_seconds: float
    max_memory_bytes: int
    max_disk_bytes: int

    def __post_init__(self) -> None:
        """Validate the ceilings one tool run must stay under when they are built."""
        if min(self.timeout_seconds, self.max_memory_bytes, self.max_disk_bytes) <= 0:
            raise ValueError("every tool limit must be positive")
