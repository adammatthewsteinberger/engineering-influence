# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The journal's models, the failure kinds, and the budget error."""

import pytest

from engineering_influence.errors.budget_exceeded_error import BudgetExceededError
from engineering_influence.models.budget import Budget
from engineering_influence.models.failure_kind import FailureKind
from engineering_influence.models.journal_entry import JournalEntry
from engineering_influence.models.journal_key import JournalKey


def key(**changes: str) -> JournalKey:
    fields = {
        "model": "claude-x-2026",
        "params_hash": "p1",
        "prompt_version": "v3",
        "context_hash": "c1",
    }
    return JournalKey(**{**fields, **changes})


def entry(**changes: object) -> JournalEntry:
    fields: dict[str, object] = {
        "run_id": "run-1",
        "stage": "draft",
        "attempt": 1,
        "key": key(),
        "response": "text",
        "cost_micro_usd": 1200,
    }
    return JournalEntry(**{**fields, **changes})  # type: ignore[arg-type]


def test_the_failure_kinds_say_what_to_do() -> None:
    assert [kind.value for kind in FailureKind] == ["transient", "capacity", "unrecoverable"]


def test_a_budget_error_is_still_a_value_error() -> None:
    assert issubclass(BudgetExceededError, ValueError)


def test_overspending_raises_the_budget_error() -> None:
    with pytest.raises(BudgetExceededError, match="exceeds the remaining budget"):
        Budget(cap=10).reserve(11)
    with pytest.raises(BudgetExceededError, match="exceeds the reservation"):
        Budget(cap=10, reserved=5).settle(5, 6)


def test_other_budget_mistakes_stay_plain_value_errors() -> None:
    with pytest.raises(ValueError, match="negative") as raised:
        Budget(cap=10).reserve(-1)
    assert not isinstance(raised.value, BudgetExceededError)


def test_the_same_request_always_has_the_same_digest() -> None:
    assert key().digest() == key().digest()
    assert len(key().digest()) == 64


@pytest.mark.parametrize("field", ["model", "params_hash", "prompt_version", "context_hash"])
def test_changing_any_part_of_the_request_changes_the_digest(field: str) -> None:
    assert key(**{field: "other"}).digest() != key().digest()


def test_parts_cannot_be_shuffled_into_the_same_digest() -> None:
    assert key(model="a", params_hash="b").digest() != key(model="b", params_hash="a").digest()
    assert key(model="ab", params_hash="c").digest() != key(model="a", params_hash="bc").digest()


@pytest.mark.parametrize("field", ["model", "params_hash", "prompt_version", "context_hash"])
def test_a_key_needs_every_part(field: str) -> None:
    with pytest.raises(ValueError, match="every part"):
        key(**{field: "  "})


def test_an_entry_records_the_answer_and_its_cost() -> None:
    value = entry()
    assert (value.response, value.cost_micro_usd, value.key.digest()) == (
        "text",
        1200,
        key().digest(),
    )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"run_id": " "}, "a run and a stage"),
        ({"stage": ""}, "a run and a stage"),
        ({"attempt": 0}, "from 1"),
        ({"cost_micro_usd": -1}, "less than nothing"),
    ],
)
def test_an_entry_refuses_what_cannot_have_happened(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        entry(**changes)
