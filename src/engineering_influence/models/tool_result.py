# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a tool gave back for one call."""

from dataclasses import dataclass, replace

from engineering_influence.models.interfaces.tool_result_interface import ToolResultInterface


@dataclass(frozen=True, slots=True)
class ToolResult(ToolResultInterface):
    """The text a tool returned for the call with this id, and whether it was an error.

    This is text from outside, so it is untrusted: it is shown to the model as evidence and never
    followed as instructions.
    """

    call_id: str
    content: str
    is_error: bool = False

    def __post_init__(self) -> None:
        if not self.call_id.strip():
            raise ValueError("a tool result answers a call by its id")

    def capped(self, limit: int) -> "ToolResult":
        """The same result with at most ``limit`` characters of content, and a note of what was cut."""
        if limit < 1:
            raise ValueError("a result limit is at least one character")
        if len(self.content) <= limit:
            return self
        omitted = len(self.content) - limit
        return replace(
            self, content=f"{self.content[:limit]}\n[truncated: {omitted} more characters]"
        )
