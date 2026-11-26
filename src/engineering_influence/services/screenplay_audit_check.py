# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The source audit's mechanical checks: its five sections are present, every source file has one verdict in order, and
every invention is marked as added for the film."""

import re
from typing import ClassVar

from engineering_influence.services.interfaces.screenplay_audit_check_interface import (
    ScreenplayAuditCheckInterface,
)


class ScreenplayAuditCheck(ScreenplayAuditCheckInterface):
    """Each section is a `## Heading` with a name in `SECTIONS`. The verdict table has one row per source file, numbered
    from 001 with no gap and no repeat. Each bullet under Inventions carries the word FILM, so nothing the film adds is
    passed off as the author's. Whether a verdict is right stays with a reader."""

    SECTIONS: ClassVar[tuple[str, ...]] = (
        "Source verdicts",
        "Internalization",
        "Source to beat",
        "Compression",
        "Inventions",
    )
    HEADING: ClassVar[re.Pattern[str]] = re.compile(r"^## (.+?)\s*$", re.MULTILINE)
    NUMBER: ClassVar[re.Pattern[str]] = re.compile(r"\d{3}")

    def problems(self, text: str) -> tuple[str, ...]:
        """Every way the audit breaks the format."""
        sections = self._sections(text)
        found = [
            f"the audit needs a '## {name}' section"
            for name in self.SECTIONS
            if name not in sections
        ]
        if "Source verdicts" in sections:
            found.extend(self._verdict_problems(sections["Source verdicts"]))
        if "Inventions" in sections:
            found.extend(self._invention_problems(sections["Inventions"]))
        return tuple(found)

    @classmethod
    def _verdict_problems(cls, body: str) -> list[str]:
        numbers = [
            int(cell.strip())
            for line in body.splitlines()
            if line.strip().startswith("|")
            and (cell := line.strip().strip("|").split("|")[0].strip())
            and cls.NUMBER.fullmatch(cell)
        ]
        if not numbers:
            return ["the source verdicts list no source files"]
        if numbers != list(range(1, len(numbers) + 1)):
            return [
                f"the source verdicts must cover the source files 001 to {len(numbers):03d}, each once and in order"
            ]
        return []

    @staticmethod
    def _invention_problems(body: str) -> list[str]:
        return [
            f"invention {line.strip()[2:]!r} is not marked FILM"
            for line in body.splitlines()
            if line.strip().startswith("- ") and "FILM" not in line
        ]

    @classmethod
    def _sections(cls, text: str) -> dict[str, str]:
        """Each section's name and the text under its heading, up to the next heading."""
        starts = list(cls.HEADING.finditer(text))
        sections: dict[str, str] = {}
        for position, match in enumerate(starts):
            end = starts[position + 1].start() if position + 1 < len(starts) else len(text)
            sections[match.group(1)] = text[match.end() : end]
        return sections
