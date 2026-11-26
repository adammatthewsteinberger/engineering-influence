# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The narrator for the non-Audible audiobook: none unless EI_NARRATOR names one, and a named one is refused until built."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.runtime.stage_executor_runtime import StageExecutorRuntime


def test_with_no_narrator_named_the_audiobook_is_not_narrated() -> None:
    assert StageExecutorRuntime._narrator({}) is None
    assert StageExecutorRuntime._narrator({"EI_NARRATOR": "   "}) is None


def test_a_named_narrator_is_refused_until_its_engine_is_built() -> None:
    with pytest.raises(ApplicationError) as error:
        StageExecutorRuntime._narrator({"EI_NARRATOR": "kokoro"})
    assert error.value.code == "NARRATOR_UNAVAILABLE"
    assert "docs/adr/0014" in error.value.message
