# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An httpx transport that passes requests on and keeps the exchanges, with secrets masked."""

import json
from typing import Any

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.cassette_recorder_interface import CassetteRecorderInterface
from engineering_influence.interfaces.cassette_store_interface import CassetteStoreInterface
from engineering_influence.interfaces.secret_redactor_interface import SecretRedactorInterface
from engineering_influence.models.cassette import Cassette
from engineering_influence.models.cassette_interaction import CassetteInteraction


class CassetteRecordingTransport(httpx.BaseTransport, CassetteRecorderInterface):
    """Wraps a real transport. The caller sees the real answer; the cassette sees a masked copy.

    Only the method, path (with its query), JSON bodies and status are kept. Headers are dropped,
    because the API key is one. A body that is not JSON cannot be recorded, so a recording stops
    with an error instead of keeping something the replay could not read back. Nothing here pays
    for anything: whoever hands it a live transport and a key is the one spending.
    """

    def __init__(
        self,
        inner: httpx.BaseTransport,
        redactor: SecretRedactorInterface,
        store: CassetteStoreInterface,
    ) -> None:
        """Remember the real transport, the redactor and the cassette store."""
        self._inner = inner
        self._redactor = redactor
        self._store = store
        self._interactions: list[CassetteInteraction] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Send the request on, keep a masked copy of the exchange, return the real answer."""
        response = self._inner.handle_request(request)
        response.read()
        self._interactions.append(
            CassetteInteraction(
                method=request.method,
                path=self._redactor.redact(request.url.raw_path.decode()),
                request_body=self._redactor.redact(self._json(request.content, "request")),
                status=response.status_code,
                response_body=self._redactor.redact(self._json(response.content, "response")),
            )
        )
        return response

    def finish(self, name: str, provider: str, note: str = "") -> Cassette:
        """Save what was recorded as the named cassette and return it."""
        if not self._interactions:
            raise ApplicationError(
                code="CASSETTE_INVALID",
                message="nothing was recorded, so there is no cassette to save",
                http_status=500,
            )
        try:
            cassette = Cassette(name, provider, tuple(self._interactions), note)
        except ValueError as error:
            raise ApplicationError(
                code="CASSETTE_INVALID", message=str(error), http_status=500
            ) from error
        self._store.save(cassette)
        return cassette

    def close(self) -> None:
        """Close the transport underneath."""
        self._inner.close()

    @staticmethod
    def _json(content: bytes, what: str) -> Any:
        if not content:
            return None
        try:
            return json.loads(content)
        except ValueError as error:
            raise ApplicationError(
                code="CASSETTE_UNRECORDABLE",
                message=f"the {what} was not JSON, and a cassette holds JSON only",
                http_status=500,
            ) from error
