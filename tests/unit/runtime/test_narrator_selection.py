# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The narrator for the non-Audible audiobook: none unless EI_NARRATOR names one. The built-in `kokoro` engine is chosen
with its voice, and any other name is refused."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.narration.kokoro_mlx_narrator import KokoroMlxNarrator
from engineering_influence.runtime.stage_executor_runtime import StageExecutorRuntime


def test_with_no_narrator_named_the_audiobook_is_not_narrated() -> None:
    assert StageExecutorRuntime._narrator({}) is None
    assert StageExecutorRuntime._narrator({"EI_NARRATOR": "   "}) is None


def test_kokoro_is_the_built_in_narrator_with_its_voice() -> None:
    narrator = StageExecutorRuntime._narrator(
        {"EI_NARRATOR": "kokoro", "EI_NARRATOR_VOICE": "bf_emma"}
    )
    assert isinstance(narrator, KokoroMlxNarrator)
    assert narrator._voice == "bf_emma"
    default = StageExecutorRuntime._narrator({"EI_NARRATOR": "kokoro"})
    assert isinstance(default, KokoroMlxNarrator) and default._voice == "af_heart"


def test_any_other_narrator_is_refused() -> None:
    with pytest.raises(ApplicationError) as error:
        StageExecutorRuntime._narrator({"EI_NARRATOR": "piper"})
    assert error.value.code == "NARRATOR_UNAVAILABLE"
    assert "kokoro" in error.value.message
