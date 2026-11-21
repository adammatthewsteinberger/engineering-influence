# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The probe lists a server's models with the profile's key, and never follows a redirect."""

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.models.http_model_probe import HttpModelProbe
from engineering_influence.interfaces.model_probe_interface import ModelProbeInterface
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_profile import ModelProfile

KEY = "sk-test-SECRETSECRET"


def probe_with(handler: httpx.MockTransport) -> HttpModelProbe:
    return HttpModelProbe(httpx.Client(transport=handler))


def anthropic() -> ModelProfile:
    return ModelProfile(
        "h", "anthropic", "a", "m", "https://api.anthropic.com/", api_key_env="ANTHROPIC_API_KEY"
    )


def local(url: str = "http://127.0.0.1:11434") -> ModelProfile:
    return ModelProfile("l", "openai_compatible", "local", "m", url)


def test_the_probe_is_a_port() -> None:
    assert isinstance(
        probe_with(httpx.MockTransport(lambda r: httpx.Response(200))), ModelProbeInterface
    )


def test_the_probe_itself_refuses_to_send_a_key_over_plain_http_to_another_host() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200)

    risky = ModelProfile("r", "openai_compatible", "p", "m", "http://10.0.0.5:8000", "K")
    with pytest.raises(ApplicationError) as caught:
        probe_with(httpx.MockTransport(handler)).probe(risky, KEY)
    assert caught.value.code == "MODEL_PROBE_FAILED"
    assert "10.0.0.5:8000" in caught.value.message
    assert KEY not in caught.value.message
    assert seen == []


def test_an_anthropic_probe_sends_its_headers_to_the_models_list() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": []})

    assert probe_with(httpx.MockTransport(handler)).probe(anthropic(), KEY) is (
        ModelAvailability.AVAILABLE
    )
    (request,) = seen
    assert request.method == "GET"
    assert str(request.url) == "https://api.anthropic.com/v1/models"
    assert request.headers["x-api-key"] == KEY
    assert request.headers["anthropic-version"] == "2023-06-01"
    assert "authorization" not in request.headers
    assert request.content == b""


def test_an_openai_compatible_probe_sends_a_bearer_token() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200)

    profile = ModelProfile("o", "openai_compatible", "p", "m", "https://x.test/", api_key_env="K")
    probe_with(httpx.MockTransport(handler)).probe(profile, KEY)
    assert seen[0].headers["authorization"] == f"Bearer {KEY}"
    assert str(seen[0].url) == "https://x.test/v1/models"
    assert "x-api-key" not in seen[0].headers


def test_a_local_probe_sends_no_authorization_header() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200)

    probe_with(httpx.MockTransport(handler)).probe(local(), "")
    assert "authorization" not in seen[0].headers
    assert "x-api-key" not in seen[0].headers


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, ModelAvailability.AUTHENTICATION_FAILED),
        (403, ModelAvailability.AUTHENTICATION_FAILED),
        (402, ModelAvailability.CREDITS_EXHAUSTED),
        (429, ModelAvailability.WINDOW_EXHAUSTED),
    ],
)
def test_the_status_says_what_the_server_thinks_of_the_key(
    status: int, expected: ModelAvailability
) -> None:
    probe = probe_with(httpx.MockTransport(lambda r: httpx.Response(status)))
    assert probe.probe(anthropic(), KEY) is expected


@pytest.mark.parametrize("status", [404, 500, 503])
def test_any_other_status_is_a_failure_that_names_the_host_and_status(status: int) -> None:
    probe = probe_with(httpx.MockTransport(lambda r: httpx.Response(status)))
    with pytest.raises(ApplicationError) as caught:
        probe.probe(local("http://127.0.0.1:11434"), "")
    assert caught.value.code == "MODEL_PROBE_FAILED"
    assert caught.value.message == f"127.0.0.1:11434 answered {status}"


def test_a_redirect_is_reported_and_the_key_is_not_sent_on() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(302, headers={"location": "https://evil.test/v1/models"})

    with pytest.raises(ApplicationError) as caught:
        probe_with(httpx.MockTransport(handler)).probe(anthropic(), KEY)
    assert "answered 302" in caught.value.message
    assert [r.url.host for r in seen] == ["api.anthropic.com"]


def test_an_unreachable_server_is_reported_without_the_key_or_the_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with pytest.raises(ApplicationError) as caught:
        probe_with(httpx.MockTransport(handler)).probe(anthropic(), KEY)
    assert caught.value.message == "api.anthropic.com could not be reached: ConnectError"
    assert KEY not in caught.value.message
