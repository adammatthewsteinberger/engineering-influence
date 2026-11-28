# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One request a model adapter sent, and the answer that came back."""

from dataclasses import dataclass
from typing import Any

from engineering_influence.models.interfaces.cassette_interaction_interface import (
    CassetteInteractionInterface,
)


@dataclass(frozen=True, slots=True)
class CassetteInteraction(CassetteInteractionInterface):
    """One recorded exchange: the request's method, path and JSON body, and the reply's.

    Headers are never stored. The API key travels in one, so a cassette that holds none cannot
    leak it. The path keeps its query string, so a replay is exact about what was asked.
    """

    method: str
    path: str
    request_body: Any
    status: int
    response_body: Any

    ABSENT = object()

    def __post_init__(self) -> None:
        """Validate the recorded request and reply when the exchange is built."""
        if not (self.method.isalpha() and self.method == self.method.upper()):
            raise ValueError("a recorded method is upper-case letters, such as 'POST'")
        if not self.path.startswith("/"):
            raise ValueError("a recorded path starts with '/'")
        if not 100 <= self.status <= 599:
            raise ValueError("a recorded status is between 100 and 599")

    def mismatch(self, method: str, path: str, body: Any) -> str:
        """Why a request is not the recorded one, or an empty string when it is.

        A body that differs is described by the names of the keys that differ, never their values.
        """
        if method != self.method:
            return f"the method was {method}, the cassette has {self.method}"
        if path != self.path:
            return f"the path was {path}, the cassette has {self.path}"
        if body == self.request_body:
            return ""
        if isinstance(body, dict) and isinstance(self.request_body, dict):
            keys = sorted(
                key
                for key in body.keys() | self.request_body.keys()
                if body.get(key, self.ABSENT) != self.request_body.get(key, self.ABSENT)
            )
            return f"the request body differs in: {', '.join(keys)}"
        return "the request body differs"
