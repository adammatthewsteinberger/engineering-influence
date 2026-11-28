# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What identifies one model request, so a repeat of it can be replayed."""

import hashlib
from dataclasses import dataclass

from engineering_influence.models.interfaces.journal_key_interface import JournalKeyInterface


@dataclass(frozen=True, slots=True)
class JournalKey(JournalKeyInterface):
    """The model snapshot, parameters, prompt version and context a request was made with."""

    model: str
    params_hash: str
    prompt_version: str
    context_hash: str

    def __post_init__(self) -> None:
        if not all(part.strip() for part in self._parts()):
            raise ValueError("every part of a journal key is required")
        # The digest joins the parts with the unit separator, so a part that contains it could make two different
        # requests share a digest. The model and prompt version come from configuration, and this refuses the one
        # character that would make them ambiguous.
        if any("\x1f" in part for part in self._parts()):
            raise ValueError("a journal key part cannot contain the unit separator")

    def digest(self) -> str:
        """A stable SHA-256 of the four parts; the same request always gives the same digest."""
        return hashlib.sha256("\x1f".join(self._parts()).encode("utf-8")).hexdigest()

    def _parts(self) -> tuple[str, ...]:
        return (self.model, self.params_hash, self.prompt_version, self.context_hash)
