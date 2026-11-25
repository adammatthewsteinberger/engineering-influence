# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ModelAnswer: complete means no issues, incomplete always says why."""

import pytest

from engineering_influence.models.model_answer import ModelAnswer
from engineering_influence.models.quality_issue import QualityIssue

ISSUE = QualityIssue("draft", "REFUSED", "declined", blocking=True)


def test_a_complete_answer_has_text_and_no_issues() -> None:
    answer = ModelAnswer("text", True, (), 5, 1, False)
    assert (answer.text, answer.complete, answer.issues) == ("text", True, ())


def test_an_incomplete_answer_may_have_no_text_but_must_have_an_issue() -> None:
    answer = ModelAnswer("", False, (ISSUE,), 5, 2, False)
    assert answer.issues == (ISSUE,)


def test_the_invariants_are_enforced() -> None:
    with pytest.raises(ValueError, match="no issues"):
        ModelAnswer("t", True, (ISSUE,), 0, 1, False)
    with pytest.raises(ValueError, match="must say what is wrong"):
        ModelAnswer("t", False, (), 0, 1, False)
    with pytest.raises(ValueError, match="cannot be negative"):
        ModelAnswer("t", True, (), -1, 1, False)
    with pytest.raises(ValueError, match="cannot be negative"):
        ModelAnswer("t", True, (), 1, -1, False)


def test_a_replay_is_complete_free_and_made_no_call() -> None:
    assert ModelAnswer("t", True, (), 0, 0, True).replayed
    with pytest.raises(ValueError, match="replayed answer"):
        ModelAnswer("t", False, (ISSUE,), 0, 0, True)
    with pytest.raises(ValueError, match="replayed answer"):
        ModelAnswer("t", True, (), 5, 0, True)
    with pytest.raises(ValueError, match="replayed answer"):
        ModelAnswer("t", True, (), 0, 1, True)
