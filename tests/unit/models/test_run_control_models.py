"""The pure models that steer a run: kinds, issues, verdicts, the budget and the ladder."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.budget import Budget
from engineering_influence.models.degrade_ladder import DegradeLadder
from engineering_influence.models.gate_verdict import GateVerdict
from engineering_influence.models.quality_issue import QualityIssue


def issue(*, blocking: bool = False) -> QualityIssue:
    return QualityIssue(stage="draft", code="thin-chapter", detail="400 words", blocking=blocking)


def test_the_two_kinds_are_the_1_0_scope() -> None:
    assert [kind.value for kind in BookKind] == ["nonfiction", "novel"]
    assert BookKind("novel") is BookKind.NOVEL


@pytest.mark.parametrize(("stage", "code"), [("", "x"), ("x", ""), ("  ", "x"), ("x", " ")])
def test_an_issue_needs_a_stage_and_a_code(stage: str, code: str) -> None:
    with pytest.raises(ValueError, match="stage and code"):
        QualityIssue(stage=stage, code=code, detail="")


def test_an_issue_is_not_blocking_unless_it_says_so() -> None:
    assert issue().blocking is False
    assert issue(blocking=True).blocking is True


def test_a_failed_verdict_must_say_why() -> None:
    with pytest.raises(ValueError, match="must say why"):
        GateVerdict(gate="copyedit", passed=False)
    failed = GateVerdict(gate="copyedit", passed=False, issues=(issue(),))
    assert failed.passed is False


def test_a_passing_verdict_may_carry_warnings_but_not_blockers() -> None:
    assert GateVerdict(gate="copyedit", passed=True, issues=(issue(),)).passed is True
    with pytest.raises(ValueError, match="blocking issue"):
        GateVerdict(gate="copyedit", passed=True, issues=(issue(blocking=True),))


def test_a_verdict_names_its_gate() -> None:
    with pytest.raises(ValueError, match="gate's name"):
        GateVerdict(gate=" ", passed=True)


def test_a_budget_reserves_then_settles_to_the_actual_cost() -> None:
    budget = Budget(cap=1_000)
    held = budget.reserve(400)
    assert (held.reserved, held.remaining()) == (400, 600)
    settled = held.settle(reserved=400, actual=250)
    assert (settled.spent, settled.reserved, settled.remaining()) == (250, 0, 750)
    assert budget == Budget(cap=1_000), "the original is untouched"


def test_a_failed_call_settles_at_zero_and_returns_the_reservation() -> None:
    held = Budget(cap=100).reserve(60)
    assert held.settle(reserved=60, actual=0) == Budget(cap=100)


def test_a_reservation_that_does_not_fit_is_refused() -> None:
    with pytest.raises(ValueError, match="exceeds the remaining budget"):
        Budget(cap=100, spent=70).reserve(31)
    assert Budget(cap=100, spent=70).reserve(30).remaining() == 0


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: Budget(cap=-1), "cannot be negative"),
        (lambda: Budget(cap=10, spent=-1), "cannot be negative"),
        (lambda: Budget(cap=10, spent=6, reserved=5), "exceed the cap"),
        (lambda: Budget(cap=10).reserve(-1), "cannot be negative"),
        (lambda: Budget(cap=10).settle(-1, 0), "cannot be negative"),
        (lambda: Budget(cap=10).settle(0, -1), "cannot be negative"),
        (lambda: Budget(cap=10, reserved=2).settle(3, 0), "more than is reserved"),
        (lambda: Budget(cap=10, reserved=5).settle(5, 6), "exceeds the reservation"),
    ],
)
def test_a_budget_refuses_impossible_amounts(call: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        call()  # type: ignore[operator]


OPERATIONS = st.lists(
    st.tuples(st.sampled_from(["reserve", "settle", "fail"]), st.integers(0, 500), st.floats(0, 1)),
    max_size=40,
)


@settings(max_examples=200, deadline=None)
@given(cap=st.integers(0, 2_000), operations=OPERATIONS)
def test_however_calls_interleave_spend_never_passes_the_cap(
    cap: int, operations: list[tuple[str, int, float]]
) -> None:
    budget = Budget(cap=cap)
    in_flight: list[int] = []
    previous_spent = 0
    for action, amount, fraction in operations:
        if action == "reserve" and amount <= budget.remaining():
            budget = budget.reserve(amount)
            in_flight.append(amount)
        elif in_flight:
            held = in_flight.pop(0)
            actual = 0 if action == "fail" else int(held * fraction)
            budget = budget.settle(held, actual)
        assert budget.spent + budget.reserved <= budget.cap
        assert budget.remaining() >= 0
        assert budget.spent >= previous_spent
        previous_spent = budget.spent
    assert budget.reserved == sum(in_flight)


def test_a_ladder_steps_down_one_rung_at_a_time_and_stops_at_the_bottom() -> None:
    ladder = DegradeLadder(rungs=("full", "no-critic", "single-pass"))
    assert (ladder.current(), ladder.exhausted()) == ("full", False)
    lower = ladder.step_down()
    assert (lower.current(), lower.exhausted()) == ("no-critic", False)
    bottom = lower.step_down()
    assert (bottom.current(), bottom.exhausted()) == ("single-pass", True)
    with pytest.raises(ValueError, match="no lower rung"):
        bottom.step_down()
    assert ladder.current() == "full", "stepping down returns a new ladder"


@pytest.mark.parametrize(
    ("rungs", "position", "message"),
    [
        ((), 0, "at least one named rung"),
        (("a", " "), 0, "at least one named rung"),
        (("a", "a"), 0, "distinct"),
        (("a", "b"), 2, "off the ladder"),
        (("a", "b"), -1, "off the ladder"),
    ],
)
def test_a_ladder_must_be_well_formed(rungs: tuple[str, ...], position: int, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        DegradeLadder(rungs=rungs, position=position)
