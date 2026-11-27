# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""StageExecutorRuntime._video_generator: no video model unless EI_VIDEO_PROVIDER names one, and a named one needs its key."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.video.openrouter_video_generator import (
    OpenRouterVideoGenerator,
)
from engineering_influence.runtime.stage_executor_runtime import StageExecutorRuntime


def test_with_no_provider_named_there_is_no_video_model() -> None:
    assert StageExecutorRuntime._video_generator({}) is None
    assert StageExecutorRuntime._video_generator({"EI_VIDEO_PROVIDER": "  "}) is None


def test_openrouter_with_its_key_is_the_video_model() -> None:
    generator = StageExecutorRuntime._video_generator(
        {"EI_VIDEO_PROVIDER": "openrouter", "EI_OPENROUTER_API_KEY": "k"}
    )
    assert isinstance(generator, OpenRouterVideoGenerator)


@pytest.mark.parametrize(
    "environment",
    [
        {"EI_VIDEO_PROVIDER": "openrouter"},
        {"EI_VIDEO_PROVIDER": "veo", "EI_OPENROUTER_API_KEY": "k"},
    ],
)
def test_a_provider_that_cannot_be_used_is_refused(environment: dict[str, str]) -> None:
    with pytest.raises(ApplicationError) as error:
        StageExecutorRuntime._video_generator(environment)
    assert error.value.code == "VIDEO_PROVIDER_UNAVAILABLE"
