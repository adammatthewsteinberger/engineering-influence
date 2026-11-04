"""Tests for stable application error metadata."""

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
