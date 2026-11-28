# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tokens one model call consumed, as the provider reported them."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.model_usage_interface import ModelUsageInterface


@dataclass(frozen=True, slots=True)
class ModelUsage(ModelUsageInterface):
    """Token counts for one call.

    ``input_tokens`` counts only the tokens billed at the full input price. Tokens read from
    or written to the prompt cache are counted separately, so the four fields never overlap.
    """

    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def __post_init__(self) -> None:
        """Validate the token counts when they are built."""
        if (
            min(
                self.input_tokens,
                self.output_tokens,
                self.cache_read_tokens,
                self.cache_write_tokens,
            )
            < 0
        ):
            raise ValueError("token counts cannot be negative")
