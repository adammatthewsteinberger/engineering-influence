# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reading and writing the TOML lock files: strict about their shape, and never left half written."""

import os
import tomllib
from pathlib import Path
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.toml_lock_file_interface import TomlLockFileInterface


class TomlLockFile(TomlLockFileInterface):
    """The shared reading, validating, writing and quoting of the TOML lock files.

    The skill, plugin and tool locks each keep their own entries and error code; this is the part
    they have in common, so a lock is read and written the same way whichever one it is.
    """

    @staticmethod
    def read(path: Path, *, table: str, version: int, code: str) -> dict[str, Any] | None:
        """The parsed lock, or None when there is no file.

        An unreadable file, invalid TOML, a top-level key other than ``version`` and ``table``, or another
        version is refused with ``code`` and names the file. Nothing is quietly dropped: a half-read lock
        would approve less, or more, than a person did.
        """
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError) as error:
            raise TomlLockFile._invalid(
                code, f"cannot read {path}: {type(error).__name__}"
            ) from error
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise TomlLockFile._invalid(code, f"{path} is not valid TOML: {error}") from error
        unknown = sorted(set(data) - {"version", table})
        if unknown:
            raise TomlLockFile._invalid(code, f"{path} has an unknown top-level key {unknown[0]!r}")
        found = data.get("version")
        if type(found) is not int or found != version:  # True and 1.0 equal 1
            raise TomlLockFile._invalid(code, f"{path} is version {found!r}; this reads {version}")
        return data

    @staticmethod
    def write(path: Path, blocks: list[str]) -> None:
        """Write the lock whole, or not at all: a temporary file is renamed over the old one."""
        temporary = path.with_name(f".{path.name}.tmp")
        # A stale file or link at the temporary name is removed, not written through. The flags then make
        # the open fail rather than follow a link planted between the removal and the open.
        temporary.unlink(missing_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(temporary, flags, 0o644), "w", encoding="utf-8") as handle:
            handle.write("\n".join(blocks))
        os.replace(temporary, path)

    @staticmethod
    def quote(text: str) -> str:
        """A TOML basic string: quotes and backslashes escaped, control characters as \\u escapes."""
        out = []
        for char in text:
            if char in '"\\':
                out.append("\\" + char)
            elif ord(char) < 0x20 or ord(char) == 0x7F:
                out.append(f"\\u{ord(char):04x}")
            else:
                out.append(char)
        return '"' + "".join(out) + '"'

    @staticmethod
    def _invalid(code: str, message: str) -> ApplicationError:
        return ApplicationError(code=code, message=message, http_status=422)
