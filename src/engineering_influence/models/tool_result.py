# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a tool gave back for one call."""

from dataclasses import dataclass, replace

from engineering_influence.models.interfaces.tool_result_interface import ToolResultInterface
from engineering_influence.models.prompt_template import PromptTemplate


@dataclass(frozen=True, slots=True)
class ToolResult(ToolResultInterface):
    """The text a tool returned for the call with this id, and whether it was an error.

    This is text from outside, so it is untrusted: it is shown to the model as evidence and never
    followed as instructions. ``untrusted`` is how it is marked as such before the model sees it.
    """

    call_id: str
    content: str
    is_error: bool = False

    def __post_init__(self) -> None:
        """Validate the result's call id and text when it is built."""
        if not self.call_id.strip():
            raise ValueError("a tool result answers a call by its id")

    def untrusted(self, name: str) -> "ToolResult":
        """The same result with its content in an ``<untrusted>`` block that it cannot close early.

        Any copy of the tag inside the content is defused first, as ``PromptTemplate`` does for a
        blank, so what a page or a server returns cannot end the block and speak outside it.
        """
        defused = PromptTemplate.UNTRUSTED_TAG.sub(
            lambda match: f"<\\{match.group(1)}{match.group(2)}", self.content
        )
        return replace(self, content=f'<untrusted name="{name}">\n{defused}\n</untrusted>')

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
