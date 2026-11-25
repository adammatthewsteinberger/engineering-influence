# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One queued job as it travels through the broker."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from engineering_influence.contracts.interfaces.job_message_interface import JobMessageInterface


class JobMessage(JobMessageInterface, BaseModel):
    """The broker message body: a version, an id, a kind such as ``pipeline.thesis``, and a payload.

    A message without ``schema_version`` is read as version 1, so messages already on the queue
    when a worker upgrades still parse. A different version is refused rather than guessed at.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = 1
    job_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    payload: dict[str, Any]

    @classmethod
    def parse(cls, body: bytes) -> "JobMessage":
        """Validate raw bytes; anything malformed raises ``pydantic.ValidationError``."""
        return cls.model_validate_json(body)
