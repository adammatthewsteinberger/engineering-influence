# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A versioned prompt, written once, with its blanks and the text that must be treated as data."""

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.prompt_template_interface import (
    PromptTemplateInterface,
)


@dataclass(frozen=True, slots=True)
class PromptTemplate(PromptTemplateInterface):
    """Named text parts with ``{{blank}}`` placeholders, and a version that goes in the journal.

    The version is part of a model call's journal key, so a replayed run reuses an answer only
    for the same prompt. That makes a text edit without a version bump a silent bug, which the
    prompt lock test refuses (see docs/PROMPTS.md).

    Rendering fills every blank in one pass: a value is never searched for further blanks, and
    a blank that is missing or not in the part is an error. A blank named in ``untrusted`` takes
    text from outside (a fetched page, a user's file): it is always rendered inside an
    ``<untrusted name="...">`` block, any copy of that tag in the value is defused first, and
    the template may not put it in the ``system`` part, which must tell the model to treat that
    block as evidence and never as instructions.
    """

    NAME: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]*")
    BLANK: ClassVar[re.Pattern[str]] = re.compile(r"\{\{\s*([a-z][a-z0-9_]*)\s*\}\}")
    UNTRUSTED_TAG: ClassVar[re.Pattern[str]] = re.compile(r"<\s*(/?)\s*(untrusted)", re.IGNORECASE)

    name: str
    version: int
    parts: Mapping[str, str]
    untrusted: frozenset[str] = frozenset()
    description: str = ""

    def __post_init__(self) -> None:
        if not self.NAME.fullmatch(self.name):
            raise ValueError("a template name is lowercase letters, digits and underscores")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("a template version is a whole number from 1")
        if not self.parts:
            raise ValueError("a template needs at least one part")
        for part, text in self.parts.items():
            if not self.NAME.fullmatch(part):
                raise ValueError(
                    f"part name {part!r} is not lowercase letters, digits, underscores"
                )
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"part {part!r} needs text")
            if "{{" in self.BLANK.sub("", text) or "}}" in self.BLANK.sub("", text):
                raise ValueError(f"part {part!r} has a stray brace pair that is not a blank")
        used = {blank for text in self.parts.values() for blank in self.BLANK.findall(text)}
        for variable in sorted(self.untrusted):
            if variable not in used:
                raise ValueError(f"untrusted blank {variable!r} is not used by any part")
        system = self.parts.get("system", "")
        for variable in sorted(self.untrusted):
            if variable in self.BLANK.findall(system):
                raise ValueError(f"untrusted blank {variable!r} cannot be in the system part")
        if self.untrusted and "untrusted" not in system.lower():
            raise ValueError(
                "a template with untrusted input needs a system part that says how to treat it"
            )

    def identifier(self) -> str:
        """The name and version, as recorded in the run journal: ``chapter_draft@3``."""
        return f"{self.name}@{self.version}"

    def render(self, part: str, values: Mapping[str, str] | None = None) -> str:
        """The part with every blank filled; the blanks and the values must match exactly."""
        if part not in self.parts:
            raise ValueError(f"template {self.name!r} has no part {part!r}")
        given = dict(values or {})
        needed = set(self.BLANK.findall(self.parts[part]))
        if needed - given.keys():
            raise ValueError(f"part {part!r} needs {sorted(needed - given.keys())}")
        if given.keys() - needed:
            raise ValueError(f"part {part!r} has no blank named {sorted(given.keys() - needed)}")
        if any(not isinstance(value, str) for value in given.values()):
            raise ValueError("a blank is filled with text")
        return self.BLANK.sub(lambda match: self._fill(match.group(1), given), self.parts[part])

    def fingerprint(self) -> str:
        """A hash of everything that changes what the model sees; the description is left out."""
        content = {
            "name": self.name,
            "version": self.version,
            "parts": dict(sorted(self.parts.items())),
            "untrusted": sorted(self.untrusted),
        }
        return hashlib.sha256(json.dumps(content, sort_keys=True).encode("utf-8")).hexdigest()

    def _fill(self, blank: str, values: Mapping[str, str]) -> str:
        value = values[blank]
        if blank not in self.untrusted:
            return value
        defused = self.UNTRUSTED_TAG.sub(lambda m: f"<\\{m.group(1)}{m.group(2)}", value)
        return f'<untrusted name="{blank}">\n{defused}\n</untrusted>'
