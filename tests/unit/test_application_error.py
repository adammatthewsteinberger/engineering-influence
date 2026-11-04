"""Tests for stable application error metadata."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError

import pytest

from engineering_influence.errors import ApplicationError


def test_application_error_exposes_transport_metadata() -> None:
    error = ApplicationError("project.missing", "Project is missing", True, 404, "PROJECT_MISSING")

    assert str(error) == "Project is missing"
    assert error.retryable is True
    assert error.http_status == 404
    assert error.mcp_error_code == "PROJECT_MISSING"


@pytest.mark.parametrize("code,message", [("", "message"), ("code", "")])
def test_application_error_rejects_empty_identity(code: str, message: str) -> None:
    with pytest.raises(ValueError, match="code and message"):
        ApplicationError(code, message)


def test_application_error_fields_stay_immutable() -> None:
    error = ApplicationError("code", "message")

    with pytest.raises(FrozenInstanceError):
        error.code = "other"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        del error.message
    assert error.code == "code"


def test_application_error_survives_exception_machinery() -> None:
    error = ApplicationError("code", "message")

    def raise_on_thread() -> None:
        raise error

    with ThreadPoolExecutor(max_workers=1) as pool, pytest.raises(ApplicationError) as caught:
        pool.submit(raise_on_thread).result()
    assert caught.value is error
    assert error.__traceback__ is not None


def test_application_error_can_be_chained_and_hashed() -> None:
    cause = ValueError("root")
    try:
        raise ApplicationError("code", "message") from cause
    except ApplicationError as error:
        assert error.__cause__ is cause
        assert hash(error) == hash(ApplicationError("code", "message"))
        assert {error: 1}[error] == 1


def test_application_error_allows_ordinary_attributes_to_change() -> None:
    error = ApplicationError("code", "message")

    error.add_note("context for the operator")
    error.detail = "extra"  # type: ignore[attr-defined]
    del error.detail  # type: ignore[attr-defined]

    assert error.__notes__ == ["context for the operator"]
    assert not hasattr(error, "detail")
