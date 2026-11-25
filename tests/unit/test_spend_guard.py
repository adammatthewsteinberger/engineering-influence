"""SpendGuard: reservations behind a lock, and the overspend rule."""

import threading

import pytest

from engineering_influence.errors.budget_exceeded_error import BudgetExceededError
from engineering_influence.models.budget import Budget
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface
from engineering_influence.services.spend_guard import SpendGuard


def test_it_is_a_guard_and_starts_from_the_budget_it_was_given() -> None:
    guard = SpendGuard(Budget(cap=100, spent=30))
    assert isinstance(guard, SpendGuardInterface)
    assert guard.budget() == Budget(cap=100, spent=30)


def test_a_reservation_is_held_and_then_settled_to_the_real_cost() -> None:
    guard = SpendGuard(Budget(cap=100))
    guard.reserve(60)
    assert guard.budget() == Budget(cap=100, reserved=60)
    guard.settle(60, 45)
    assert guard.budget() == Budget(cap=100, spent=45)


def test_a_reservation_that_does_not_fit_holds_nothing() -> None:
    guard = SpendGuard(Budget(cap=100, spent=50))
    with pytest.raises(BudgetExceededError):
        guard.reserve(51)
    assert guard.budget() == Budget(cap=100, spent=50)
    guard.reserve(50)
    assert guard.budget().remaining() == 0


def test_release_gives_the_whole_reservation_back() -> None:
    guard = SpendGuard(Budget(cap=100))
    guard.reserve(80)
    guard.release(80)
    assert guard.budget() == Budget(cap=100)


def test_an_overrun_books_what_was_reserved_releases_it_and_raises() -> None:
    guard = SpendGuard(Budget(cap=100))
    guard.reserve(40)
    with pytest.raises(BudgetExceededError):
        guard.settle(40, 41)
    assert guard.budget() == Budget(cap=100, spent=40, reserved=0)


def test_settling_more_than_is_reserved_is_a_programming_error_that_changes_nothing() -> None:
    guard = SpendGuard(Budget(cap=100))
    guard.reserve(10)
    with pytest.raises(ValueError, match="more than is reserved"):
        guard.settle(11, 0)
    assert guard.budget() == Budget(cap=100, reserved=10)


def test_many_threads_reserving_at_once_never_pass_the_cap() -> None:
    guard = SpendGuard(Budget(cap=50))
    start = threading.Barrier(200)
    won: list[int] = []

    def grab() -> None:
        start.wait()
        try:
            guard.reserve(1)
        except BudgetExceededError:
            return
        won.append(1)

    threads = [threading.Thread(target=grab) for _ in range(200)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(won) == 50
    assert guard.budget() == Budget(cap=50, reserved=50)
