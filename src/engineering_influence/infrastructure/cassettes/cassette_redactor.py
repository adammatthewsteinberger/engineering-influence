# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Masks API keys in anything headed for a cassette."""

import re
from collections.abc import Iterable
from typing import Any, ClassVar

from engineering_influence.interfaces.secret_redactor_interface import SecretRedactorInterface


class CassetteRedactor(SecretRedactorInterface):
    """Replaces each named secret, and anything shaped like a vendor key, with a mask.

    The named secrets are the real defence: the recorder is told the key it was run with. The key
    shape (``sk-`` and sixteen more characters, not inside a word) is a backstop for a key that was
    not named. It is deliberately narrow, so ordinary prose such as ``task-management-workflows``
    is left alone.
    """

    MASK = "[REDACTED]"
    MINIMUM_LENGTH = 6
    SHAPE: ClassVar[re.Pattern[str]] = re.compile(r"(?<![A-Za-z0-9_])sk-[A-Za-z0-9_-]{16,}")

    def __init__(self, secrets: Iterable[str] = ()) -> None:
        named = sorted(set(secrets), key=len, reverse=True)
        for secret in named:
            if len(secret.strip()) < self.MINIMUM_LENGTH or secret != secret.strip():
                raise ValueError(
                    f"a secret to mask is at least {self.MINIMUM_LENGTH} characters with no "
                    "surrounding space; an unset key would otherwise mask ordinary text"
                )
        self._secrets = named

    def redact(self, value: Any) -> Any:
        """The same data with every secret replaced by a mask."""
        if isinstance(value, str):
            return self._text(value)
        if isinstance(value, dict):
            return {self._text(str(key)): self.redact(item) for key, item in value.items()}
        if isinstance(value, list | tuple):
            return [self.redact(item) for item in value]
        return value

    def leaks(self, value: Any) -> bool:
        """True when the data still holds something that redacting would change."""
        if isinstance(value, str):
            return self._text(value) != value
        if isinstance(value, dict):
            return any(self.leaks(str(key)) or self.leaks(item) for key, item in value.items())
        if isinstance(value, list | tuple):
            return any(self.leaks(item) for item in value)
        return False

    def _text(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, self.MASK)
        return self.SHAPE.sub(self.MASK, text)
