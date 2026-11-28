# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""OpenRouterVideoGenerator: submit, poll until completed, then download; each failure is classed the way a run needs."""

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.video.openrouter_video_generator import (
    OpenRouterVideoGenerator,
)
from engineering_influence.models.video_shot import VideoShot

SHOT = VideoShot(7, 2, "minimax/hailuo-3", 4, "A door shuts.")


def generator(handler, sleeps: list[float] | None = None) -> OpenRouterVideoGenerator:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenRouterVideoGenerator(
        client, " key ", sleep=(sleeps.append if sleeps is not None else lambda _: None)
    )


def completing(states: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"id": "job1"})
        if request.url.path.endswith("/content"):
            return httpx.Response(200, content=b"MP4")
        return httpx.Response(200, json={"status": states.pop(0)})

    return handler


def test_a_shot_is_submitted_polled_and_downloaded_with_the_key() -> None:
    seen: list[httpx.Request] = []
    states = ["in_progress", "completed"]
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return completing(states)(request)

    data = generator(handler, sleeps).generate(SHOT)
    assert data == b"MP4"
    submit = seen[0]
    assert submit.method == "POST" and submit.url.path == "/api/v1/videos"
    assert submit.headers["authorization"] == "Bearer key"
    assert b'"model":"minimax/hailuo-3"' in submit.content
    assert b'"duration":4' in submit.content
    assert sleeps == [OpenRouterVideoGenerator.POLL_SECONDS]


def test_a_job_that_fails_is_an_application_error() -> None:
    with pytest.raises(ApplicationError) as error:
        generator(completing(["failed"])).generate(SHOT)
    assert error.value.code == "VIDEO_GENERATION_FAILED"
    assert "shot 7" in error.value.message


def test_a_job_that_never_finishes_is_retried_later() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"id": "job1"})
        return httpx.Response(200, json={"status": "in_progress"})

    with pytest.raises(TransientStageError):
        generator(handler).generate(SHOT)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (402, CapacityExhaustedError),
        (401, CapacityExhaustedError),
        (429, TransientStageError),
        (503, TransientStageError),
        (400, ApplicationError),
    ],
)
def test_a_refused_submit_is_classed_by_its_status(status: int, expected: type) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text="no")

    with pytest.raises(expected):
        generator(handler).generate(SHOT)


def test_a_service_that_cannot_be_reached_is_retried_later() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    with pytest.raises(TransientStageError):
        generator(handler).generate(SHOT)
