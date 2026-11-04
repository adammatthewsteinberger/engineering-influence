# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One queued job as it travels through the broker."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobMessage(BaseModel):
    """The broker message body: an id, a kind such as ``pipeline.thesis``, and a payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    payload: dict[str, Any]

    @classmethod
    def parse(cls, body: bytes) -> "JobMessage":
        """Validate raw bytes; anything malformed raises ``pydantic.ValidationError``."""
        return cls.model_validate_json(body)
