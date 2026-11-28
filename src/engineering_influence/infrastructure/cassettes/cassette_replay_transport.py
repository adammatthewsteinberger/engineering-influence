# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An httpx transport that answers from a cassette, never from the network."""

import json
from typing import Any

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.cassette_player_interface import CassettePlayerInterface
from engineering_influence.interfaces.secret_redactor_interface import SecretRedactorInterface
from engineering_influence.models.cassette import Cassette


class CassetteReplayTransport(httpx.BaseTransport, CassettePlayerInterface):
    """Replays the recorded exchanges in order, and refuses anything that is not the next one.

    A request must match the next recorded one in method, path and JSON body, so a prompt that
    changed since the recording fails the test instead of quietly replaying a stale answer. A
    refusal is an ApplicationError (CASSETTE_MISMATCH), not an httpx error, so an adapter cannot
    mistake it for a network failure and retry. ``finish`` fails the test if the code stopped
    asking before the cassette ran out.

    The request is masked with the redactor before it is compared, as the recorder masked it. So a
    cassette recorded under one key replays under another, and a refusal never prints a key.
    """

    def __init__(self, cassette: Cassette, redactor: SecretRedactorInterface) -> None:
        """Remember the cassette to replay and the redactor applied to each request."""
        self._cassette = cassette
        self._redactor = redactor
        self._position = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """The next recorded answer, if this request is the next recorded request."""
        path = self._redactor.redact(request.url.raw_path.decode())
        label = f"{request.method} {path}"
        recorded = self._cassette.interaction_at(self._position)
        if recorded is None:
            raise self._refused(
                f"cassette {self._cassette.name!r} has {len(self._cassette.interactions)} "
                f"exchanges and the code asked for another: {label}"
            )
        problem = recorded.mismatch(
            request.method, path, self._redactor.redact(self._body(request, label))
        )
        if problem:
            raise self._refused(
                f"request {self._position + 1} of cassette {self._cassette.name!r} "
                f"({label}) does not match: {problem}"
            )
        self._position += 1
        return httpx.Response(recorded.status, json=recorded.response_body)

    def remaining(self) -> int:
        """How many recorded exchanges have not been replayed yet."""
        return len(self._cassette.interactions) - self._position

    def finish(self) -> None:
        """Raise an ApplicationError (CASSETTE_MISMATCH) if any recorded exchange was never replayed."""
        if self.remaining():
            raise self._refused(
                f"{self.remaining()} of {len(self._cassette.interactions)} exchanges in cassette "
                f"{self._cassette.name!r} were never replayed"
            )

    def _body(self, request: httpx.Request, label: str) -> Any:
        if not request.content:
            return None
        try:
            return json.loads(request.content)
        except ValueError as error:
            raise self._refused(f"the body of {label} is not JSON") from error

    @staticmethod
    def _refused(message: str) -> ApplicationError:
        return ApplicationError(code="CASSETTE_MISMATCH", message=message, http_status=500)
