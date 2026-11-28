# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ShootingLockCodec: a lock written as JSON reads back the same, and anything else is refused as unreadable."""

import json

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.shooting_lock import ShootingLock
from engineering_influence.models.shooting_lock_entry import ShootingLockEntry
from engineering_influence.services.shooting_lock_codec import ShootingLockCodec

CODEC = ShootingLockCodec()


def unreadable(text: str, reason: str) -> None:
    with pytest.raises(ApplicationError) as error:
        CODEC.decode(text)
    assert error.value.code == "SHOOTING_LOCK_UNREADABLE"
    assert reason in error.value.message


def test_a_lock_reads_back_as_the_same_lock() -> None:
    lock = ShootingLock((ShootingLockEntry(1, "1", False), ShootingLockEntry(2, "42A", True)))
    assert CODEC.decode(CODEC.encode(lock)) == lock


def test_a_lock_is_written_as_a_version_one_object_with_its_scenes() -> None:
    data = json.loads(CODEC.encode(ShootingLock((ShootingLockEntry(3, "3", False),))))
    assert data == {"version": 1, "entries": [{"card": 3, "label": "3", "omitted": False}]}


def test_text_that_is_not_json_is_unreadable() -> None:
    unreadable("{", "it is not JSON")


def test_a_lock_of_another_version_is_unreadable() -> None:
    unreadable('{"version": 2, "entries": []}', "it is not a version 1 lock")


def test_a_lock_that_is_not_an_object_is_unreadable() -> None:
    unreadable("[]", "it is not a version 1 lock")


def test_a_lock_without_a_list_of_scenes_is_unreadable() -> None:
    unreadable('{"version": 1}', "it has no list of scenes")


def test_a_scene_that_is_not_an_object_is_unreadable() -> None:
    unreadable('{"version": 1, "entries": [3]}', "is an object")


def test_a_scene_with_a_field_missing_is_unreadable() -> None:
    unreadable('{"version": 1, "entries": [{"card": 1, "label": "1"}]}', "unreadable")


def test_a_scene_with_a_bad_number_is_unreadable() -> None:
    unreadable(
        '{"version": 1, "entries": [{"card": 1, "label": "1B2", "omitted": false}]}',
        "at most one capital letter",
    )
