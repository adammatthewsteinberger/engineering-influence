# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Ollama server port."""

from __future__ import annotations

from abc import ABC, abstractmethod


class OllamaServerInterface(ABC):
    """What the doctor asks an Ollama server about itself, without asking any model anything."""

    __slots__ = ()

    @abstractmethod
    def models(self) -> tuple[str, ...] | None:
        """The names of the models pulled onto the server, or None when it answers but is not Ollama.

        Raise an ApplicationError (LOCAL_SERVER_UNREACHABLE) when nothing answers.
        """

    @abstractmethod
    def loaded_context(self, model: str) -> int | None:
        """The context length the server loaded ``model`` with, or None when it does not say."""
