# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a model sent back."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.model_response_interface import (
    ModelResponseInterface,
)
from engineering_influence.models.model_usage import ModelUsage


@dataclass(frozen=True, slots=True)
class ModelResponse(ModelResponseInterface):
    """The text, the tokens it cost, the exact model snapshot and why generation stopped.

    ``stop_reason`` is one of ``end_turn``, ``max_tokens`` or ``refusal``; an adapter maps
    its provider's wording onto these three so callers never branch on a vendor string.
    """

    text: str
    usage: ModelUsage
    model_snapshot: str
    stop_reason: str

    def __post_init__(self) -> None:
        if self.stop_reason not in ("end_turn", "max_tokens", "refusal"):
            raise ValueError(f"unknown stop reason {self.stop_reason!r}")
        if not self.model_snapshot.strip():
            raise ValueError("a response names the model snapshot that produced it")

    def was_truncated(self) -> bool:
        """True when the model hit its output cap before it finished."""
        return self.stop_reason == "max_tokens"

    def was_refused(self) -> bool:
        """True when the model declined to answer."""
        return self.stop_reason == "refusal"
