"""CallModel: replay, reserve, call, journal, settle."""

import threading
import time
from collections.abc import Callable

import pytest

from engineering_influence.errors.budget_exceeded_error import BudgetExceededError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.budget import Budget
from engineering_influence.models.journal_entry import JournalEntry
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_call_result import ModelCallResult
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.services.call_model import CallModel
from engineering_influence.services.interfaces.call_model_interface import CallModelInterface
from engineering_influence.services.spend_guard import SpendGuard

# 1 micro-USD per input token, 5 per output token, cache write 1.25.
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
REQUEST = ModelRequest(system="s", prompt="hello there", max_output_tokens=100, prompt_version="v1")
# 10 counted tokens at the dearer 1.25 rate (12.5) + 100 output tokens at 5 (500) = 512.5, rounded up.
RESERVATION = 513
# 10 input and 20 output tokens really used: 10 + 100.
ACTUAL = 110


def answer(
    text: str = "done", usage: ModelUsage | None = None, stop: str = "end_turn"
) -> ModelResponse:
    return ModelResponse(text, usage or ModelUsage(10, 20), "fake-1-snap", stop)


class ScriptedModel(ModelInterface):
    """Replies from a script; can run a hook inside the call, and says how many tokens it counts."""

    def __init__(self, *script: ModelResponse | BaseException, counted: int = 10) -> None:
        self.script = list(script)
        self.counted = counted
        self.calls: list[ModelRequest] = []
        self.during: Callable[[], None] | None = None

    def describe(self) -> ProviderDescriptor:
        return DESCRIPTOR

    def availability(self) -> ModelAvailability:
        return ModelAvailability.AVAILABLE

    def count_tokens(self, request: ModelRequest) -> int:
        return self.counted

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        if self.during is not None:
            self.during()
        item = self.script.pop(0) if self.script else answer()
        if isinstance(item, BaseException):
            raise item
        return item


def setup(*script: ModelResponse | BaseException, cap: int = 10_000, counted: int = 10):  # type: ignore[no-untyped-def]
    model = ScriptedModel(*script, counted=counted)
    journal = InMemoryJournal()
    guard = SpendGuard(Budget(cap=cap))
    return model, journal, guard, CallModel(model, journal)


def test_a_first_call_is_made_journaled_and_paid_for() -> None:
    model, journal, guard, caller = setup(answer("Chapter one."))
    assert isinstance(caller, CallModelInterface)
    result = caller.call(guard, "run-1", "draft", 1, REQUEST)

    assert result == ModelCallResult("Chapter one.", "end_turn", ACTUAL, False)
    assert len(model.calls) == 1
    (entry,) = journal.entries("run-1")
    assert (entry.stage, entry.attempt, entry.response, entry.cost_micro_usd) == (
        "draft",
        1,
        "Chapter one.",
        ACTUAL,
    )
    assert (entry.key.model, entry.key.prompt_version) == ("fake-1", "v1")
    assert guard.budget() == Budget(cap=10_000, spent=ACTUAL)


def test_the_worst_case_is_held_while_the_call_is_in_flight() -> None:
    model, _, guard, caller = setup()
    seen: list[Budget] = []
    model.during = lambda: seen.append(guard.budget())
    caller.call(guard, "run-1", "draft", 1, REQUEST)
    assert seen == [Budget(cap=10_000, reserved=RESERVATION)]


def test_a_repeat_of_the_same_request_is_replayed_for_nothing() -> None:
    model, journal, guard, caller = setup(answer("Chapter one."))
    caller.call(guard, "run-1", "draft", 1, REQUEST)
    again = caller.call(guard, "run-1", "draft", 2, REQUEST)

    assert again == ModelCallResult("Chapter one.", "end_turn", 0, True)
    assert len(model.calls) == 1
    assert len(journal.entries("run-1")) == 1
    assert guard.budget() == Budget(cap=10_000, spent=ACTUAL)


@pytest.mark.parametrize(
    "other",
    [
        ModelRequest("s", "a different prompt", 100, "v1"),
        ModelRequest("another system", "hello there", 100, "v1"),
        ModelRequest("s", "hello there", 101, "v1"),
        ModelRequest("s", "hello there", 100, "v2"),
    ],
)
def test_any_change_to_the_request_is_a_new_call(other: ModelRequest) -> None:
    model, journal, guard, caller = setup()
    caller.call(guard, "run-1", "draft", 1, REQUEST)
    result = caller.call(guard, "run-1", "draft", 1, other)
    assert result.replayed is False
    assert len(model.calls) == 2
    assert len(journal.entries("run-1")) == 2


def test_moving_the_boundary_between_system_and_prompt_is_a_different_request() -> None:
    # Joined with a separator, both pairs would read "a<sep>b<sep>c" and share one journal key.
    first = ModelRequest("a\x1eb", "c", 100, "v1")
    second = ModelRequest("a", "b\x1ec", 100, "v1")
    model, _, guard, caller = setup(answer("first"), answer("second"))
    one = caller.call(guard, "run-1", "draft", 1, first)
    two = caller.call(guard, "run-1", "draft", 1, second)
    assert (one.text, two.text) == ("first", "second")
    assert two.replayed is False
    assert len(model.calls) == 2


def test_the_same_request_in_another_stage_or_run_is_not_replayed() -> None:
    model, _, guard, caller = setup()
    caller.call(guard, "run-1", "draft", 1, REQUEST)
    caller.call(guard, "run-1", "revise", 1, REQUEST)
    caller.call(guard, "run-2", "draft", 1, REQUEST)
    assert len(model.calls) == 3


def test_a_call_that_does_not_fit_sends_nothing_and_journals_nothing() -> None:
    model, journal, guard, caller = setup(cap=RESERVATION - 1)
    with pytest.raises(BudgetExceededError):
        caller.call(guard, "run-1", "draft", 1, REQUEST)
    assert model.calls == []
    assert journal.entries("run-1") == []
    assert guard.budget() == Budget(cap=RESERVATION - 1)


def test_a_call_that_just_fits_is_made() -> None:
    model, _, guard, caller = setup(cap=RESERVATION)
    caller.call(guard, "run-1", "draft", 1, REQUEST)
    assert len(model.calls) == 1


@pytest.mark.parametrize(
    "error", [TransientStageError("rate limited"), CapacityExhaustedError("no credit")]
)
def test_a_failed_call_releases_its_reservation_and_journals_nothing(error: Exception) -> None:
    _model, journal, guard, caller = setup(error)
    with pytest.raises(type(error)):
        caller.call(guard, "run-1", "draft", 1, REQUEST)
    assert journal.entries("run-1") == []
    assert guard.budget() == Budget(cap=10_000)


def test_a_failure_that_is_not_an_exception_subclass_still_releases() -> None:
    _model, _, guard, caller = setup(KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        caller.call(guard, "run-1", "draft", 1, REQUEST)
    assert guard.budget() == Budget(cap=10_000)


@pytest.mark.parametrize("stop", ["max_tokens", "refusal"])
def test_a_truncated_or_refused_answer_is_paid_for_and_journaled_but_never_replayed(
    stop: str,
) -> None:
    model, journal, guard, caller = setup(
        answer("It was a dark and", stop=stop), answer("Full answer.")
    )
    first = caller.call(guard, "run-1", "draft", 1, REQUEST)
    assert first == ModelCallResult("It was a dark and", stop, ACTUAL, False)
    assert sum(e.cost_micro_usd for e in journal.entries("run-1")) == ACTUAL

    second = caller.call(guard, "run-1", "draft", 2, REQUEST)
    assert second == ModelCallResult("Full answer.", "end_turn", ACTUAL, False)
    assert len(model.calls) == 2
    assert sum(e.cost_micro_usd for e in journal.entries("run-1")) == 2 * ACTUAL
    assert guard.budget() == Budget(cap=10_000, spent=2 * ACTUAL)


def test_two_truncated_attempts_are_both_counted_in_the_journal() -> None:
    _, journal, guard, caller = setup(
        answer("cut", stop="max_tokens"), answer("cut", stop="max_tokens")
    )
    caller.call(guard, "run-1", "draft", 1, REQUEST)
    caller.call(guard, "run-1", "draft", 2, REQUEST)
    assert [e.attempt for e in journal.entries("run-1")] == [1, 2]
    assert sum(e.cost_micro_usd for e in journal.entries("run-1")) == 2 * ACTUAL


def test_a_call_that_costs_more_than_reserved_is_journaled_then_refused() -> None:
    # The counter said 10 tokens but the call really used 5,000: the reservation was too small.
    huge = ModelUsage(5_000, 20)
    _model, journal, guard, caller = setup(answer("paid", usage=huge))
    with pytest.raises(BudgetExceededError):
        caller.call(guard, "run-1", "draft", 1, REQUEST)
    (entry,) = journal.entries("run-1")
    assert entry.cost_micro_usd == DESCRIPTOR.cost_micro_usd(huge)
    assert guard.budget() == Budget(cap=10_000, spent=RESERVATION)


def test_concurrent_calls_reserve_together_so_only_those_that_fit_are_made() -> None:
    fit = 3
    model, journal, guard, caller = setup(cap=fit * RESERVATION + RESERVATION - 1)
    release = threading.Event()
    model.during = lambda: release.wait(5)
    outcomes: list[str] = []

    def go(index: int) -> None:
        request = ModelRequest("s", f"prompt {index}", 100, "v1")
        try:
            caller.call(guard, "run-1", "draft", 1, request)
            outcomes.append("made")
        except BudgetExceededError:
            outcomes.append("refused")

    threads = [threading.Thread(target=go, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + 5
    while len(outcomes) < 8 - fit and time.monotonic() < deadline:
        time.sleep(0.01)
    assert guard.budget().reserved == fit * RESERVATION
    release.set()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["made"] * fit + ["refused"] * (8 - fit)
    assert len(model.calls) == fit
    assert guard.budget() == Budget(cap=fit * RESERVATION + RESERVATION - 1, spent=fit * ACTUAL)
    assert sum(e.cost_micro_usd for e in journal.entries("run-1")) == fit * ACTUAL


def test_a_result_is_validated() -> None:
    with pytest.raises(ValueError, match="stop reason"):
        ModelCallResult("t", "length", 0, False)
    with pytest.raises(ValueError, match="less than nothing"):
        ModelCallResult("t", "end_turn", -1, False)
    with pytest.raises(ValueError, match="replay is free"):
        ModelCallResult("t", "end_turn", 5, True)
    with pytest.raises(ValueError, match="replay is free"):
        ModelCallResult("t", "max_tokens", 0, True)


class StaleJournal(InMemoryJournal):
    """Its first lookup finds nothing, as when another worker records the answer a moment later."""

    def __init__(self) -> None:
        super().__init__()
        self.lookups = 0

    def find(self, run_id: str, stage: str, digest: str) -> JournalEntry | None:
        self.lookups += 1
        return None if self.lookups == 1 else super().find(run_id, stage, digest)


def test_when_another_worker_journaled_the_request_first_its_answer_is_the_one_returned() -> None:
    model = ScriptedModel(answer("ours"))
    journal = StaleJournal()
    guard = SpendGuard(Budget(cap=10_000))
    caller = CallModel(model, journal)
    # Record the first worker's answer under the key our own call will compute.
    probe_journal = InMemoryJournal()
    CallModel(ScriptedModel(answer("theirs")), probe_journal).call(
        SpendGuard(Budget(cap=10_000)), "run-1", "draft", 1, REQUEST
    )
    for entry in probe_journal.entries("run-1"):
        journal.record(entry)
    journal.lookups = 0  # the setup above used the stale lookup; the caller's must be the first

    result = caller.call(guard, "run-1", "draft", 2, REQUEST)

    assert result.text == "theirs"
    assert len(journal.entries("run-1")) == 1
