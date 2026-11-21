# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Model port: one provider's model behind a single call."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.model_availability import ModelAvailability
    from engineering_influence.models.model_request import ModelRequest
    from engineering_influence.models.model_response import ModelResponse
    from engineering_influence.models.provider_descriptor import ProviderDescriptor


class ModelInterface(ABC):
    """A language model the pipeline can call, whichever provider serves it.

    ``complete`` raises ``TransientStageError`` for a timeout, a rate limit or a server error,
    ``CapacityExhaustedError`` when credit is gone or authentication fails, and any other
    exception for a failure retrying cannot fix.
    """

    __slots__ = ()

    @abstractmethod
    def describe(self) -> ProviderDescriptor:
        """The model's identity, limits, prices and usage policy."""

    @abstractmethod
    def availability(self) -> ModelAvailability:
        """Whether a call would be accepted now, without spending anything."""

    @abstractmethod
    def count_tokens(self, request: ModelRequest) -> int:
        """How many input tokens the request will use, before it is sent."""

    @abstractmethod
    def complete(self, request: ModelRequest) -> ModelResponse:
        """Send the request and return the response."""
