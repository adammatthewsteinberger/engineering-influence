# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One call to a model: what to say and how much it may say back."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.model_request_interface import (
    ModelRequestInterface,
)


@dataclass(frozen=True, slots=True)
class ModelRequest(ModelRequestInterface):
    """A system prompt, a user prompt, an output cap and the version of the prompt template.

    ``prompt_version`` is recorded in the run journal with the request hash, so a changed
    template is never mistaken for a replay of an old call.
    """

    system: str
    prompt: str
    max_output_tokens: int
    prompt_version: str

    def __post_init__(self) -> None:
        if not self.prompt.strip():
            raise ValueError("a model request needs a prompt")
        if self.max_output_tokens <= 0:
            raise ValueError("a model request needs a positive output cap")
        if not self.prompt_version.strip():
            raise ValueError("a model request needs a prompt version")
