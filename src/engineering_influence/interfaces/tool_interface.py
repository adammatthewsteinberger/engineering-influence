# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: one tool a model may call."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engineering_influence.models.tool_definition import ToolDefinition


class ToolInterface(ABC):
    """A named tool with a schema, and the code that runs it."""

    __slots__ = ()

    @abstractmethod
    def definition(self) -> ToolDefinition:
        """What the model is told about this tool."""

    def refuses(self, arguments: Mapping[str, Any], evidence: str) -> str:
        """Why this call may not run, or an empty string when it may.

        ``evidence`` is what the model has legitimately been shown in this conversation, and only
        that: the stage's own prompt, and for each earlier successful call the part its tool
        names in ``shown``. It never includes an error message, text a page or a server wrote
        outside what ``shown`` picks out, or anything the model typed. A tool whose arguments could
        carry data out (an address the model chose) can insist that they came from there. A refusal
        is answered to the model as an error and is not journaled, so it cannot stick to a later,
        permitted call. The default allows everything.
        """
        return ""

    def shown(self, result: str) -> str:
        """The part of a successful result of this tool that counts as having been shown.

        Only text the tool itself produced from a trusted source belongs here (a list of links a
        search returned, the address a fetch finally read), never text a page or a person wrote.
        The default is nothing: a tool's output does not count as evidence unless it says so.
        """
        return ""

    def revision(self) -> str:
        """What a stored result of this tool depends on besides its name and arguments.

        A result is replayed by tool and arguments. A tool whose answers change when it is replaced
        (a locked server that was updated and locked again) names that here, so a run resumed after
        the change asks again instead of replaying the old server's answers. The default is nothing.
        """
        return ""

    @abstractmethod
    def invoke(self, arguments: Mapping[str, Any]) -> str:
        """Run the tool and return its text.

        Raise ``ApplicationError`` for a failure the model should hear about and may work around
        (a page that is gone, an argument that makes no sense). Raise ``TransientStageError`` or
        ``CapacityExhaustedError`` for a failure the run should handle: they are not shown to the
        model. The result is untrusted text and is treated as such.
        """
