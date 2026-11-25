# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A prompt that has been fitted to a token budget, and what it gave up to fit."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.assembled_context_interface import (
    AssembledContextInterface,
)


@dataclass(frozen=True, slots=True)
class AssembledContext(AssembledContextInterface):
    """The system and user text to send, the tokens they were measured at, and what was cut.

    ``input_tokens`` is what the model's own counter reported for exactly this text.
    """

    system: str
    prompt: str
    input_tokens: int
    kept_summaries: int
    omitted_summaries: int
    tail_characters: int

    def __post_init__(self) -> None:
        if not self.system.strip() or not self.prompt.strip():
            raise ValueError("an assembled context needs a system and a prompt")
        if (
            min(
                self.input_tokens, self.kept_summaries, self.omitted_summaries, self.tail_characters
            )
            < 0
        ):
            raise ValueError("assembled context counts cannot be negative")
