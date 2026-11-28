# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Makes one video shot with OpenRouter's video API: submit, poll until the job is done, then download the MP4."""

import time
from collections.abc import Callable
from typing import Any, ClassVar

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.video_generator_interface import VideoGeneratorInterface
from engineering_influence.models.video_shot import VideoShot


class OpenRouterVideoGenerator(VideoGeneratorInterface):
    """Submits a job with POST /api/v1/videos, polls GET /api/v1/videos/{id} until it completes, then reads the bytes from
    GET /api/v1/videos/{id}/content. A submit starts a paid job, so the stage prices every shot before the first call.
    The request body fields follow OpenRouter's video reference and are checked by a pilot run before any paid stage.
    """

    BASE_URL: ClassVar[str] = "https://openrouter.ai/api/v1"
    POLL_SECONDS: ClassVar[float] = 20.0
    MAX_POLLS: ClassVar[int] = 30
    FAILED_STATES: ClassVar[frozenset[str]] = frozenset({"failed", "cancelled", "expired"})

    def __init__(
        self,
        client: httpx.Client,
        api_key: str,
        sleep: Callable[[float], None] = time.sleep,
        base_url: str = BASE_URL,
    ) -> None:
        """Remember the HTTP client, the key, the sleep used between polls, and the service address."""
        self._client = client
        self._api_key = api_key.strip()
        self._sleep = sleep
        self._base_url = base_url.rstrip("/")

    def generate(self, shot: VideoShot) -> bytes:
        """Start a video job for the shot, wait for it to finish, and return the video's bytes."""
        job = self._json(
            "POST",
            "/videos",
            {
                "model": shot.model(),
                "prompt": shot.prompt,
                "duration": shot.seconds(),
            },
        )
        job_id = str(job["id"])
        for _ in range(self.MAX_POLLS):
            state = str(self._json("GET", f"/videos/{job_id}", None).get("status", ""))
            if state == "completed":
                return self._content(job_id)
            if state in self.FAILED_STATES:
                raise ApplicationError(
                    code="VIDEO_GENERATION_FAILED",
                    message=f"the video service ended job {job_id} as {state!r} for shot {shot.number}",
                    http_status=502,
                )
            self._sleep(self.POLL_SECONDS)
        raise TransientStageError(
            f"video job {job_id} for shot {shot.number} did not finish in time"
        )

    def _content(self, job_id: str) -> bytes:
        response = self._send("GET", f"/videos/{job_id}/content", None)
        return response.content

    def _json(self, method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        payload: dict[str, Any] = self._send(method, path, body).json()
        return payload

    def _send(self, method: str, path: str, body: dict[str, Any] | None) -> httpx.Response:
        headers = {"authorization": f"Bearer {self._api_key}"}
        try:
            response = self._client.request(
                method, self._base_url + path, json=body, headers=headers
            )
        except httpx.TransportError as error:
            raise TransientStageError(
                f"the video service could not be reached: {type(error).__name__}"
            ) from error
        if response.status_code in (200, 201, 202):
            return response
        raise self._failure(response)

    @staticmethod
    def _failure(response: httpx.Response) -> Exception:
        status = response.status_code
        message = response.text[:300]
        if status == 402:
            return CapacityExhaustedError(f"the video account is out of credit: {message}")
        if status in (401, 403):
            return CapacityExhaustedError(
                f"the video service refused the API key ({status}): {message}"
            )
        if status in (408, 429) or status >= 500:
            return TransientStageError(f"the video service answered {status}: {message}")
        return ApplicationError(
            code="VIDEO_REJECTED",
            message=f"the video service rejected the request ({status}): {message}",
            http_status=502,
        )
