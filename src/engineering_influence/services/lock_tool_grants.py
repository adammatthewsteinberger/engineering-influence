# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The grants a tool lock records, as the executor reads them."""

from engineering_influence.interfaces.tool_grants_interface import ToolGrantsInterface
from engineering_influence.models.tool_lock import ToolLock


class LockToolGrants(ToolGrantsInterface):
    """What a person granted in the lock, and nothing else.

    A stage the lock does not mention gets nothing, so a locked server's tools are never offered
    to a stage by default, and a server added to the lock reaches no stage until a grant says so.
    """

    def __init__(self, lock: ToolLock) -> None:
        """Remember the tool lock whose grants are used."""
        self._lock = lock

    def for_stage(self, stage: str, servers: tuple[str, ...] | None = None) -> tuple[str, ...]:
        """The model names of the tools granted to the stage; none when it has no grant."""
        return self._lock.granted(stage, servers)
