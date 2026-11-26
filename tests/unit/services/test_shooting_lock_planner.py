# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ShootingLockPlanner: locked numbers stay, a new scene takes the next free number after the scene before it, and an
omitted scene keeps its place and its number."""

import pytest

from engineering_influence.models.shooting_lock import ShootingLock
from engineering_influence.models.shooting_lock_entry import ShootingLockEntry
from engineering_influence.services.shooting_lock_planner import ShootingLockPlanner

PLANNER = ShootingLockPlanner()


def lock(*rows: tuple[int, str, bool]) -> ShootingLock:
    return ShootingLock(
        tuple(ShootingLockEntry(card, label, omitted) for card, label, omitted in rows)
    )


def rows(planned: ShootingLock) -> list[tuple[int, str, bool]]:
    return [(entry.card, entry.label, entry.omitted) for entry in planned.entries]


def test_a_first_script_is_numbered_from_one() -> None:
    planned = PLANNER.plan(ShootingLock(), (1, 2, 3))
    assert rows(planned) == [(1, "1", False), (2, "2", False), (3, "3", False)]


def test_locked_scenes_keep_their_numbers_when_the_script_is_planned_again() -> None:
    previous = lock((1, "1", False), (2, "2", False))
    assert rows(PLANNER.plan(previous, (1, 2))) == [(1, "1", False), (2, "2", False)]


def test_a_new_scene_at_the_end_takes_the_next_whole_number() -> None:
    previous = lock((1, "1", False), (2, "2", False))
    assert rows(PLANNER.plan(previous, (1, 2, 3)))[-1] == (3, "3", False)


def test_a_new_scene_between_locked_scenes_takes_the_next_letter() -> None:
    previous = lock((1, "41", False), (2, "42", False), (3, "43", False))
    assert rows(PLANNER.plan(previous, (1, 2, 9, 3))) == [
        (1, "41", False),
        (2, "42", False),
        (9, "42A", False),
        (3, "43", False),
    ]


def test_each_further_insert_after_the_same_scene_takes_the_next_letter() -> None:
    previous = lock((1, "42", False), (2, "43", False))
    assert rows(PLANNER.plan(previous, (1, 8, 9, 2))) == [
        (1, "42", False),
        (8, "42A", False),
        (9, "42B", False),
        (2, "43", False),
    ]


def test_a_scene_with_no_free_number_before_it_refuses_the_plan() -> None:
    previous = lock((1, "42", False), (2, "42A", False))
    with pytest.raises(ValueError, match="no scene number fits between 42 and 42A"):
        PLANNER.plan(previous, (1, 9, 2))


def test_a_scene_after_z_takes_the_next_whole_number_when_the_letters_run_out() -> None:
    previous = lock((1, "42Z", False), (2, "43A", False))
    assert rows(PLANNER.plan(previous, (1, 9, 2)))[1] == (9, "43", False)


def test_a_scene_before_the_first_locked_scene_is_0A() -> None:
    assert rows(PLANNER.plan(lock((1, "1", False)), (9, 1)))[0] == (9, "0A", False)


def test_no_free_number_before_the_first_scene_refuses_the_plan() -> None:
    with pytest.raises(ValueError, match="between the start and 0A"):
        PLANNER.plan(lock((1, "0A", False)), (9, 1))


def test_a_scene_the_script_drops_stays_in_place_as_omitted() -> None:
    previous = lock((1, "1", False), (2, "2", False), (3, "3", False))
    assert rows(PLANNER.plan(previous, (1, 3))) == [
        (1, "1", False),
        (2, "2", True),
        (3, "3", False),
    ]


def test_a_scene_that_comes_back_keeps_its_old_number() -> None:
    previous = lock((1, "1", False), (2, "2", True), (3, "3", False))
    assert rows(PLANNER.plan(previous, (1, 2, 3))) == [
        (1, "1", False),
        (2, "2", False),
        (3, "3", False),
    ]


def test_a_locked_scene_that_has_moved_refuses_the_plan() -> None:
    previous = lock((1, "1", False), (2, "2", False))
    with pytest.raises(ValueError, match="has moved"):
        PLANNER.plan(previous, (2, 1))


def test_a_card_in_the_script_twice_refuses_the_plan() -> None:
    with pytest.raises(ValueError, match="appears once"):
        PLANNER.plan(ShootingLock(), (1, 1))
