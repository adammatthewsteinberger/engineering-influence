# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""AskModel: escalate a cut-off, retry a refusal without rewording it, and replay for free."""

import pytest

from engineering_influence.errors.budget_exceeded_error import BudgetExceededError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.budget import Budget
from engineering_influence.models.model_answer import ModelAnswer
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.services.ask_model import AskModel
from engineering_influence.services.call_model import CallModel
from engineering_influence.services.interfaces.ask_model_interface import AskModelInterface
from engineering_influence.services.spend_guard import SpendGuard

# 1 micro-USD per input token and 5 per output token; the model's own output limit is 1,000.
DESCRIPTOR = ProviderDescriptor(
    provider="fake",
    model="fake-1",
    family="fake",
    context_window=10_000,
    max_output_tokens=1_000,
    input_micro_usd_per_mtok=1_000_000,
    output_micro_usd_per_mtok=5_000_000,
    cache_read_micro_usd_per_mtok=100_000,
    cache_write_micro_usd_per_mtok=1_250_000,
    batch_discount_percent=50,
    price_effective="2026-11-01",
    usage_policy_url="https://example.test/policy",
)
# Every call here really uses 10 input and 20 output tokens: 10 + 100 micro-USD.
CALL_COST = 110


def reply(text: str, stop: str = "end_turn") -> ModelResponse:
    return ModelResponse(text, ModelUsage(10, 20), "fake-1-snap", stop)


CUT = "The tide came in and the keeper"
DONE = "The tide came in and the keeper climbed the stairs."
NO = "I can't help with that."


class ScriptedModel(ModelInterface):
    def __init__(self, *script: ModelResponse | BaseException) -> None:
        self.script = list(script)
        self.calls: list[ModelRequest] = []

    def describe(self) -> ProviderDescriptor:
        return DESCRIPTOR

    def availability(self) -> ModelAvailability:
        return ModelAvailability.AVAILABLE

    def count_tokens(self, request: ModelRequest) -> int:
        return 10

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def request(cap: int = 100) -> ModelRequest:
    return ModelRequest(system="s", prompt="write", max_output_tokens=cap, prompt_version="v1")


def setup(*script: ModelResponse | BaseException, cap: int = 1_000_000, **options: int):  # type: ignore[no-untyped-def]
    model = ScriptedModel(*script)
    journal = InMemoryJournal()
    guard = SpendGuard(Budget(cap=cap))
    return model, journal, guard, AskModel(CallModel(model, journal), model, **options)


def caps(model: ScriptedModel) -> list[int]:
    return [call.max_output_tokens for call in model.calls]


def test_a_complete_answer_comes_back_after_one_call() -> None:
    model, _, guard, asker = setup(reply(DONE))
    assert isinstance(asker, AskModelInterface)
    got = asker.ask(guard, "run", "draft", 1, request())
    assert got == ModelAnswer(DONE, True, (), CALL_COST, 1, False)
    assert caps(model) == [100]


def test_a_cut_off_is_asked_again_with_double_the_room() -> None:
    model, _, guard, asker = setup(reply(CUT, "max_tokens"), reply(DONE))
    got = asker.ask(guard, "run", "draft", 1, request(100))
    assert got == ModelAnswer(DONE, True, (), 2 * CALL_COST, 2, False)
    assert caps(model) == [100, 200]
    assert guard.budget().spent == 2 * CALL_COST  # both calls were paid for


def test_the_room_grows_to_the_models_own_limit_and_no_further() -> None:
    model, _, guard, asker = setup(
        reply(CUT, "max_tokens"), reply(CUT, "max_tokens"), reply(DONE), max_attempts=5
    )
    asker.ask(guard, "run", "draft", 1, request(400))
    assert caps(model) == [400, 800, 1_000]


def test_a_cut_off_at_the_limit_is_returned_with_a_blocking_issue_and_not_retried() -> None:
    model, _, guard, asker = setup(reply(CUT, "max_tokens"))
    got = asker.ask(guard, "run", "draft", 1, request(1_000))
    assert caps(model) == [1_000]
    assert (got.text, got.complete, got.calls) == (CUT, False, 1)
    (issue,) = got.issues
    assert (issue.stage, issue.code, issue.blocking) == ("draft", "TRUNCATED", True)
    assert "1000 tokens" in issue.detail and "part-way" in issue.detail


def test_the_attempts_are_bounded_even_when_the_room_could_grow_further() -> None:
    model, _, guard, asker = setup(
        reply(CUT, "max_tokens"), reply("longer cut", "max_tokens"), max_attempts=2
    )
    got = asker.ask(guard, "run", "draft", 1, request(100))
    assert caps(model) == [100, 200]
    assert (got.text, got.complete, got.calls, got.cost_micro_usd) == (
        "longer cut",
        False,
        2,
        2 * CALL_COST,
    )
    assert [issue.code for issue in got.issues] == ["TRUNCATED"]


def test_a_refusal_is_asked_again_unchanged_and_a_second_answer_is_used() -> None:
    model, _, guard, asker = setup(reply(NO, "refusal"), reply(DONE))
    got = asker.ask(guard, "run", "draft", 1, request())
    assert (got.text, got.complete, got.issues, got.calls) == (DONE, True, (), 2)
    assert model.calls[0] == model.calls[1]  # never reworded, never pressed


def test_a_model_that_keeps_declining_gives_no_text_and_a_blocking_issue() -> None:
    model, _, guard, asker = setup(reply(NO, "refusal"), reply(NO, "refusal"))
    got = asker.ask(guard, "run", "draft", 1, request())
    assert len(model.calls) == 2
    assert (got.text, got.complete, got.calls, got.cost_micro_usd) == ("", False, 2, 2 * CALL_COST)
    (issue,) = got.issues
    assert (issue.code, issue.blocking) == ("REFUSED", True)
    assert NO in issue.detail and "2 attempt(s)" in issue.detail


def test_the_refusal_in_the_issue_is_one_short_line() -> None:
    long_no = "I can't\nhelp with that.\n\n" + "x" * 1_000
    _, _, guard, asker = setup(reply(long_no, "refusal"), reply(long_no, "refusal"))
    (issue,) = asker.ask(guard, "run", "draft", 1, request()).issues
    excerpt = issue.detail.split(": ", 1)[1]
    assert "\n" not in excerpt and len(excerpt) == AskModel.REFUSAL_EXCERPT
    assert excerpt.startswith("I can't help with that. xxx")


def test_no_refusal_retries_means_one_call() -> None:
    model, _, guard, asker = setup(reply(NO, "refusal"), refusal_retries=0)
    got = asker.ask(guard, "run", "draft", 1, request())
    assert len(model.calls) == 1 and [i.code for i in got.issues] == ["REFUSED"]


def test_a_cut_off_that_ends_in_a_refusal_keeps_the_text_and_both_issues() -> None:
    _, _, guard, asker = setup(
        reply(CUT, "max_tokens"), reply(NO, "refusal"), reply(NO, "refusal"), max_attempts=3
    )
    got = asker.ask(guard, "run", "draft", 1, request())
    assert (got.text, got.complete) == (CUT, False)
    assert [issue.code for issue in got.issues] == ["TRUNCATED", "REFUSED"]


def test_a_refusal_followed_by_a_cut_off_reports_only_the_cut_off() -> None:
    _, _, guard, asker = setup(
        reply(NO, "refusal"), reply(CUT, "max_tokens"), max_attempts=2, refusal_retries=1
    )
    got = asker.ask(guard, "run", "draft", 1, request(1_000))
    assert (got.text, [issue.code for issue in got.issues]) == (CUT, ["TRUNCATED"])


def test_a_resumed_run_replays_the_answer_it_already_has_for_nothing() -> None:
    _, journal, guard, asker = setup(reply(CUT, "max_tokens"), reply(DONE))
    asker.ask(guard, "run", "draft", 1, request(100))
    fresh_model = ScriptedModel()  # a resumed process: no script, so any call would fail
    resumed = AskModel(CallModel(fresh_model, journal), fresh_model)
    again = resumed.ask(SpendGuard(Budget(cap=1_000_000)), "run", "draft", 1, request(100))
    assert again == ModelAnswer(DONE, True, (), 0, 0, True)
    assert fresh_model.calls == []


def test_a_resumed_run_does_not_pay_for_the_cut_off_attempts_that_led_to_its_answer() -> None:
    _, journal, guard, asker = setup(
        reply(CUT, "max_tokens"), reply(CUT, "max_tokens"), reply(DONE), max_attempts=3
    )
    asker.ask(guard, "run", "draft", 1, request(100))
    fresh = SpendGuard(Budget(cap=1_000_000))
    fresh_model = ScriptedModel()
    got = AskModel(CallModel(fresh_model, journal), fresh_model).ask(
        fresh, "run", "draft", 1, request(100)
    )
    assert (got.text, got.replayed, fresh.budget().spent) == (DONE, True, 0)


def test_an_incomplete_answer_is_not_replayed_so_a_resume_tries_again() -> None:
    _, journal, guard, asker = setup(reply(NO, "refusal"), reply(NO, "refusal"))
    asker.ask(guard, "run", "draft", 1, request())
    model = ScriptedModel(reply(DONE))
    got = AskModel(CallModel(model, journal), model).ask(guard, "run", "draft", 2, request())
    assert (got.text, got.replayed, got.calls) == (DONE, False, 1)


def test_every_call_is_journaled_under_its_own_attempt_and_its_cost_counted() -> None:
    _, journal, guard, asker = setup(
        reply(NO, "refusal"), reply(NO, "refusal"), reply(NO, "refusal"), reply(NO, "refusal")
    )
    asker.ask(guard, "run", "draft", 1, request())
    asker.ask(guard, "run", "draft", 2, request())  # the stage's own retry
    attempts = [entry.attempt for entry in journal.entries("run")]
    assert attempts == [4, 5, 8, 9]  # attempt * max_attempts + i: nothing collides
    assert guard.budget().spent == 4 * CALL_COST


def test_running_out_of_money_passes_through_and_nothing_is_swallowed() -> None:
    model, _, guard, asker = setup(reply(CUT, "max_tokens"), reply(DONE), cap=700)
    with pytest.raises(BudgetExceededError):
        asker.ask(guard, "run", "draft", 1, request(100))
    # The first call reserves its worst case (513) and settles at 110; the second, at twice the
    # output cap, needs about 1,013 more, which the cap of 700 cannot hold.
    assert caps(model) == [100]


def test_a_provider_failure_passes_through_for_the_run_to_retry() -> None:
    _, _, guard, asker = setup(TransientStageError("503"))
    with pytest.raises(TransientStageError):
        asker.ask(guard, "run", "draft", 1, request())


def test_the_options_are_validated() -> None:
    model = ScriptedModel()
    with pytest.raises(ValueError, match="at least one attempt"):
        AskModel(CallModel(model, InMemoryJournal()), model, max_attempts=0)
    with pytest.raises(ValueError, match="cannot be negative"):
        AskModel(CallModel(model, InMemoryJournal()), model, refusal_retries=-1)


def test_a_request_already_above_the_models_limit_is_not_escalated() -> None:
    model, _, guard, asker = setup(reply(CUT, "max_tokens"))
    got = asker.ask(guard, "run", "draft", 1, request(5_000))
    assert caps(model) == [5_000] and [i.code for i in got.issues] == ["TRUNCATED"]
