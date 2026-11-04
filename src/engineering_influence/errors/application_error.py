"""Typed errors shared by every interaction surface."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApplicationError(Exception):
    """An interaction-neutral error with stable transport metadata."""

    code: str
    message: str
    retryable: bool = False
    http_status: int = 400
    mcp_error_code: str = "APPLICATION_ERROR"

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError("application error code and message are required")
        Exception.__init__(self, self.message)
