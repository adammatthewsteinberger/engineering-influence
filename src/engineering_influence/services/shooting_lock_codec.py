# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes the shooting script lock as JSON, and reads it back, refusing anything it cannot read."""

import json
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.shooting_lock import ShootingLock
from engineering_influence.models.shooting_lock_entry import ShootingLockEntry
from engineering_influence.services.interfaces.shooting_lock_codec_interface import (
    ShootingLockCodecInterface,
)


class ShootingLockCodec(ShootingLockCodecInterface):
    """A version, then each scene's card, label and omitted flag, in script order. The version is checked on the way
    in, so a lock written by a later version of this code is refused rather than misread."""

    VERSION: ClassVar[int] = 1

    def encode(self, lock: ShootingLock) -> str:
        entries = [
            {"card": entry.card, "label": entry.label, "omitted": entry.omitted}
            for entry in lock.entries
        ]
        return json.dumps({"version": self.VERSION, "entries": entries}, indent=2) + "\n"

    def decode(self, text: str) -> ShootingLock:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise self._unreadable("it is not JSON") from error
        if not isinstance(data, dict) or data.get("version") != self.VERSION:
            raise self._unreadable(f"it is not a version {self.VERSION} lock")
        if not isinstance(data.get("entries"), list):
            raise self._unreadable("it has no list of scenes")
        try:
            return ShootingLock(tuple(self._entry(item) for item in data["entries"]))
        except (KeyError, TypeError, ValueError) as error:
            raise self._unreadable(str(error)) from error

    @staticmethod
    def _entry(item: object) -> ShootingLockEntry:
        if not isinstance(item, dict):
            raise TypeError("a scene in the lock is an object")
        return ShootingLockEntry(item["card"], item["label"], item["omitted"])

    @staticmethod
    def _unreadable(reason: str) -> ApplicationError:
        return ApplicationError(
            code="SHOOTING_LOCK_UNREADABLE",
            message=f"the shooting script lock is unreadable: {reason}",
            http_status=422,
        )
