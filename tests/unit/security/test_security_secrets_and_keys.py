"""Fail-closed secrets and API key verification."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.security.constant_time_api_key_verifier import (
    ConstantTimeApiKeyVerifier,
)
from engineering_influence.infrastructure.security.env_secret_provider import EnvSecretProvider

KEY = "k" * 24
OTHER = "o" * 30


def test_secret_is_returned_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EI_TEST_SECRET", "  value  ")

    assert EnvSecretProvider().require("EI_TEST_SECRET") == "value"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_or_blank_secret_stops_the_service(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv("EI_TEST_SECRET", raising=False)
    else:
        monkeypatch.setenv("EI_TEST_SECRET", value)

    with pytest.raises(ApplicationError) as caught:
        EnvSecretProvider().require("EI_TEST_SECRET")
    assert caught.value.code == "SECRET_MISSING"
    assert caught.value.http_status == 503
    assert "EI_TEST_SECRET" in caught.value.message


def test_verifier_accepts_only_configured_keys() -> None:
    verifier = ConstantTimeApiKeyVerifier([KEY, OTHER])

    assert verifier.verify(KEY)
    assert verifier.verify(OTHER)
    assert not verifier.verify("x" * 24)
    assert not verifier.verify(KEY + "x")
    assert not verifier.verify(KEY[:-1])


@pytest.mark.parametrize("presented", [None, "", " "])
def test_verifier_refuses_missing_input(presented: str | None) -> None:
    assert not ConstantTimeApiKeyVerifier([KEY]).verify(presented)


def test_verifier_trims_configured_keys() -> None:
    assert ConstantTimeApiKeyVerifier([f"  {KEY}  "]).verify(KEY)


@pytest.mark.parametrize("keys", [[], [""], ["  "]])
def test_verifier_cannot_be_built_without_keys(keys: list[str]) -> None:
    with pytest.raises(ValueError, match="at least one"):
        ConstantTimeApiKeyVerifier(keys)


def test_verifier_rejects_weak_keys() -> None:
    with pytest.raises(ValueError, match="at least"):
        ConstantTimeApiKeyVerifier([KEY, "short"])


def test_verifier_reads_comma_separated_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EI_API_KEYS", f"{KEY}, {OTHER} ,")
    verifier = ConstantTimeApiKeyVerifier.from_secrets(EnvSecretProvider())

    assert verifier.verify(KEY) and verifier.verify(OTHER)


def test_unconfigured_api_keys_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EI_API_KEYS", raising=False)

    with pytest.raises(ApplicationError, match="EI_API_KEYS"):
        ConstantTimeApiKeyVerifier.from_secrets(EnvSecretProvider())
