# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Typed errors shared by every interaction surface."""

from dataclasses import FrozenInstanceError, dataclass
from typing import Any


@dataclass(slots=True, unsafe_hash=True)
class ApplicationError(Exception):
    """An interaction-neutral error with stable transport metadata.

    The declared fields are immutable once set. ``frozen=True`` is not used because it
    also blocks the interpreter from assigning ``__traceback__``, which breaks any
    framework that raises the error on a worker thread.
    """

    code: str
    message: str
    retryable: bool = False
    http_status: int = 400
    mcp_error_code: str = "APPLICATION_ERROR"

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError("application error code and message are required")
        Exception.__init__(self, self.message)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in self.__dataclass_fields__ and hasattr(self, name):
            raise FrozenInstanceError(f"cannot assign to field {name!r}")
        Exception.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        if name in self.__dataclass_fields__:
            raise FrozenInstanceError(f"cannot delete field {name!r}")
        Exception.__delattr__(self, name)
