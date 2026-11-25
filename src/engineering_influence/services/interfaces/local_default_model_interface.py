# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for LocalDefaultModel."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.model_profile import ModelProfile
    from engineering_influence.models.provider_descriptor import ProviderDescriptor


class LocalDefaultModelInterface(ABC):
    """The free, open-source model a run uses when nothing else is chosen."""

    __slots__ = ()

    @abstractmethod
    def profile(self) -> ModelProfile:
        """How to reach it: an OpenAI-compatible server on this machine, no key."""

    @abstractmethod
    def descriptor(self) -> ProviderDescriptor:
        """Its limits and its price, which is nothing."""
