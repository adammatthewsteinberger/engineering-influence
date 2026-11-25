# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A run never spends past its cap, whatever order its calls reserve, settle, overrun and give up."""

from hypothesis import given, settings
from hypothesis import strategies as st

from engineering_influence.errors.budget_exceeded_error import BudgetExceededError
from engineering_influence.models.budget import Budget
from engineering_influence.services.spend_guard import SpendGuard

STEP = st.one_of(
    st.tuples(st.just("reserve"), st.integers(0, 4_000_000)),
    st.tuples(st.just("settle"), st.integers(0, 9), st.integers(0, 100)),
    st.tuples(
        st.just("overrun"), st.integers(0, 9), st.one_of(st.just(1), st.integers(1, 1_000_000))
    ),
    st.tuples(st.just("reserve"), st.just(0)),
    st.tuples(st.just("release"), st.integers(0, 9)),
)


@settings(max_examples=400, deadline=None)
@given(
    steps=st.lists(STEP, max_size=60),
    cap=st.integers(min_value=0, max_value=5_000_000),
    already_spent=st.integers(min_value=0, max_value=5_000_000),
)
def test_no_order_of_reserving_settling_overrunning_and_releasing_passes_the_cap(
    steps: list[tuple[int | str, ...]], cap: int, already_spent: int
) -> None:
    already_spent = min(already_spent, cap)
    guard = SpendGuard(Budget(cap=cap, spent=already_spent))
    # The reservations that are in flight, as the calls that made them hold them.
    held: list[int] = []
    spent = already_spent

    for action, *arguments in steps:
        before = guard.budget()
        if action == "reserve":
            amount = int(arguments[0])
            try:
                guard.reserve(amount)
            except BudgetExceededError:
                assert guard.budget() == before  # a reservation that does not fit holds nothing
                assert amount > before.remaining()
            else:
                held.append(amount)
        elif held:
            reserved = held.pop(int(arguments[0]) % len(held))
            if action == "settle":
                actual = min(reserved, reserved * int(arguments[1]) // 100)
                guard.settle(reserved, actual)
                spent += actual
            elif action == "release":
                guard.release(reserved)
            else:
                try:
                    guard.settle(reserved, reserved + int(arguments[1]))
                except BudgetExceededError:
                    spent += reserved  # the overrun books what was reserved, never more
                else:
                    raise AssertionError("an overrun was accepted")

        now = guard.budget()
        assert now.cap == cap
        assert now.spent + now.reserved <= cap  # the one rule: never past the cap
        assert now.spent == spent  # what is booked is exactly what calls settled
        assert now.reserved == sum(held)  # and what is held is exactly what is in flight
        assert now.remaining() >= 0
