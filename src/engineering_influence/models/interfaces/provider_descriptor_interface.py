# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ProviderDescriptor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.model_usage import ModelUsage


class ProviderDescriptorInterface(ABC):
    """Everything the run must know about one model before calling it."""

    __slots__ = ()

    @abstractmethod
    def cost_micro_usd(self, usage: ModelUsage, batch: bool = False) -> int:
        """What a finished call cost, rounded up to a whole micro-dollar."""

    @abstractmethod
    def worst_case_micro_usd(self, input_tokens: int, max_output_tokens: int) -> int:
        """The most a call can cost, to reserve before sending it."""
