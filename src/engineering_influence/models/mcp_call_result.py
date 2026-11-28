# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What an MCP tool answered."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.mcp_call_result_interface import (
    McpCallResultInterface,
)


@dataclass(frozen=True, slots=True)
class McpCallResult(McpCallResultInterface):
    """The text of a tool's answer, and whether the server marked it as a failure.

    Only text is kept. Anything else a server sends back (an image, a resource, audio) is replaced
    by a note that it was left out, because a model here reads text and nothing else.
    """

    text: str
    is_error: bool

    def __post_init__(self) -> None:
        """Validate the tool's answer when the result is built."""
        if not isinstance(self.text, str):
            raise TypeError("a tool answers in text")
