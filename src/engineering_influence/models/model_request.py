# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One call to a model: what to say and how much it may say back."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.model_request_interface import (
    ModelRequestInterface,
)
from engineering_influence.models.model_turn import ModelTurn
from engineering_influence.models.tool_definition import ToolDefinition


@dataclass(frozen=True, slots=True)
class ModelRequest(ModelRequestInterface):
    """A system prompt, a user prompt, an output cap and the version of the prompt template.

    ``prompt_version`` is recorded in the run journal with the request hash, so a changed
    template is never mistaken for a replay of an old call.

    ``tools`` are what the model may call. ``transcript`` is the rounds of a conversation so far:
    each one is what the model said and called, and what came back, in order after the prompt.
    """

    system: str
    prompt: str
    max_output_tokens: int
    prompt_version: str
    tools: tuple[ToolDefinition, ...] = ()
    transcript: tuple[ModelTurn, ...] = ()

    def __post_init__(self) -> None:
        if not self.prompt.strip():
            raise ValueError("a model request needs a prompt")
        if self.max_output_tokens <= 0:
            raise ValueError("a model request needs a positive output cap")
        if not self.prompt_version.strip():
            raise ValueError("a model request needs a prompt version")
        if not isinstance(self.tools, tuple) or not isinstance(self.transcript, tuple):
            raise TypeError("tools and transcript are tuples")
        if len({tool.name for tool in self.tools}) != len(self.tools):
            raise ValueError("a request offers each tool once")
        if self.transcript and not self.tools:
            raise ValueError("a transcript of tool calls goes with the tools that were offered")
