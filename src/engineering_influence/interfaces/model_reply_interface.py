# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for reading a successful model reply, and for the error when the reply is not the one expected."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx

    from engineering_influence.errors.application_error import ApplicationError


class ModelReplyInterface(ABC):
    """Reads the JSON object a model server answers with, and names what was not understood."""

    __slots__ = ()

    @staticmethod
    @abstractmethod
    def body(response: httpx.Response, label: str) -> dict[str, Any]:
        """The JSON object of a successful reply, or MODEL_RESPONSE_UNEXPECTED naming `label`."""

    @staticmethod
    @abstractmethod
    def unexpected(label: str, what: str) -> ApplicationError:
        """The error for a reply in a shape the adapter does not understand."""
