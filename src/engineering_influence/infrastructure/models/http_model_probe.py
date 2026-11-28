# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Ask a model server whether it accepts a key, using its model-list endpoint (ADR 0007)."""

from typing import ClassVar
from urllib.parse import urlsplit

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.models.anthropic_model import AnthropicModel
from engineering_influence.interfaces.model_probe_interface import ModelProbeInterface
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_profile import ModelProfile


class HttpModelProbe(ModelProbeInterface):
    """``GET /v1/models`` with the profile's key; no completion is ever requested.

    It tells you the server is reachable and accepts the key. It cannot tell you the account has
    credit, or that the model you named is served: a listing can be paged, so an absent name
    proves nothing. It refuses to send a key over plain http to another machine. A redirect is reported, never followed, because following one would send the
    key to a host nobody configured. The client is injected and carries the timeout.
    """

    STATUS: ClassVar[dict[int, ModelAvailability]] = {
        401: ModelAvailability.AUTHENTICATION_FAILED,
        403: ModelAvailability.AUTHENTICATION_FAILED,
        402: ModelAvailability.CREDITS_EXHAUSTED,
        429: ModelAvailability.WINDOW_EXHAUSTED,
    }

    def __init__(self, client: httpx.Client) -> None:
        """Remember the HTTP client."""
        self._client = client

    def probe(self, profile: ModelProfile, api_key: str) -> ModelAvailability:
        """What the server's answer says about the key."""
        if profile.sends_key_in_clear():
            raise self._failed(
                f"{self._host(profile)} is plain http and the key would be sent in clear; use https"
            )
        headers: dict[str, str] = {}
        if profile.adapter == "anthropic":
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = AnthropicModel.API_VERSION
        elif api_key:
            headers["authorization"] = f"Bearer {api_key}"
        url = profile.base_url.rstrip("/") + "/v1/models"
        try:
            response = self._client.get(url, headers=headers, follow_redirects=False)
        except httpx.TransportError as error:
            raise self._failed(
                f"{self._host(profile)} could not be reached: {type(error).__name__}"
            ) from error
        if response.status_code == 200:
            return ModelAvailability.AVAILABLE
        known = self.STATUS.get(response.status_code)
        if known is not None:
            return known
        raise self._failed(f"{self._host(profile)} answered {response.status_code}")

    @staticmethod
    def _host(profile: ModelProfile) -> str:
        parts = urlsplit(profile.base_url)
        return parts.netloc

    @staticmethod
    def _failed(message: str) -> ApplicationError:
        return ApplicationError(code="MODEL_PROBE_FAILED", message=message, http_status=502)
