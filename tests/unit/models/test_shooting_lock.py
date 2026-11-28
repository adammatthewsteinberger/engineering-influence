# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ShootingLockEntry and ShootingLock: a label is a number with at most one capital letter, and a lock keeps its scenes in
script order, each card and each number once."""

import pytest

from engineering_influence.models.shooting_lock import ShootingLock
from engineering_influence.models.shooting_lock_entry import ShootingLockEntry


def entry(card: int, label: str, omitted: bool = False) -> ShootingLockEntry:
    return ShootingLockEntry(card, label, omitted)


def test_a_label_is_a_number_with_at_most_one_capital_letter() -> None:
    assert entry(1, "42").sort_key() == (42, "")
    assert entry(1, "42A").sort_key() == (42, "A")
    for label in ("", "A", "42a", "42AB", "4 2"):
        with pytest.raises(ValueError, match="at most one capital letter"):
            entry(1, label)


def test_a_scene_card_is_numbered_from_one() -> None:
    with pytest.raises(ValueError, match="numbered from 1"):
        entry(0, "1")


def test_an_omitted_flag_is_a_bool() -> None:
    with pytest.raises(ValueError, match="omitted or not"):
        ShootingLockEntry(1, "1", "no")  # type: ignore[arg-type]


def test_a_lock_locks_each_card_and_each_number_once() -> None:
    with pytest.raises(ValueError, match="locked once"):
        ShootingLock((entry(1, "1"), entry(1, "2")))
    with pytest.raises(ValueError, match="used once"):
        ShootingLock((entry(1, "1"), entry(2, "1")))


def test_a_lock_runs_in_script_order() -> None:
    with pytest.raises(ValueError, match="script order"):
        ShootingLock((entry(1, "2"), entry(2, "1")))
    lock = ShootingLock((entry(1, "1"), entry(2, "42A"), entry(3, "43", omitted=True)))
    assert lock.numbered_cards() == (1, 2, 3)


def test_an_empty_lock_has_no_cards() -> None:
    assert ShootingLock().numbered_cards() == ()
