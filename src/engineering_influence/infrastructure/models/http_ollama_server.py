# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Ask an Ollama server which models it has and how it loaded one, over its own HTTP interface."""

from typing import Any

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.ollama_server_interface import OllamaServerInterface


class HttpOllamaServer(OllamaServerInterface):
    """``GET /api/tags`` for the pulled models and ``GET /api/ps`` for what is loaded and with what context.

    Neither endpoint runs a model. A server that answers ``/api/tags`` with anything but a model list is not Ollama
    (llama.cpp and vLLM do not have it), which is reported as ``None`` rather than as a failure. What the server
    says is only compared, never printed. The client is injected and carries the timeout.
    """

    MAX_MODELS = 500

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    def models(self) -> tuple[str, ...] | None:
        """The names of the models pulled onto the server, or None when it answers but is not Ollama."""
        try:
            response = self._client.get(f"{self._base_url}/api/tags")
        except httpx.HTTPError as error:
            raise ApplicationError(
                code="LOCAL_SERVER_UNREACHABLE",
                message=f"nothing answers at {self._base_url}",
                http_status=503,
            ) from error
        entries = self._entries(response)
        if entries is None:
            return None
        return tuple(str(entry["name"]) for entry in entries[: self.MAX_MODELS] if "name" in entry)

    def loaded_context(self, model: str) -> int | None:
        """The context length the server loaded ``model`` with, or None when it does not say."""
        try:
            response = self._client.get(f"{self._base_url}/api/ps")
        except httpx.HTTPError:
            return None
        for entry in self._entries(response) or []:
            if entry.get("name") in (model, f"{model}:latest"):
                length = entry.get("context_length")
                return length if type(length) is int else None
        return None

    @staticmethod
    def _entries(response: httpx.Response) -> list[dict[str, Any]] | None:
        if response.status_code != 200:
            return None
        try:
            entries = response.json()["models"]
        except (ValueError, KeyError, TypeError):
            return None
        if not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries):
            return None
        return entries
