# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Outcome of a security check that must never leak why in detail."""

from pydantic import BaseModel, ConfigDict


class SecurityVerdict(BaseModel):
    """Accepted, or rejected with a short stable reason code."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    accepted: bool
    reason: str | None = None

    @classmethod
    def accept(cls) -> "SecurityVerdict":
        """Return the accepting verdict."""
        return cls(accepted=True)

    @classmethod
    def reject(cls, reason: str) -> "SecurityVerdict":
        """Return a rejecting verdict carrying a stable reason code."""
        return cls(accepted=False, reason=reason)
