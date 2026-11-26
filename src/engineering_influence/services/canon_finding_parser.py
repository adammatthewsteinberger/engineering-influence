# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads the canon check's findings: each `ERROR where: [rule] message` or `WARN where: [rule] message` line."""

import re
from typing import ClassVar

from engineering_influence.models.canon_finding import CanonFinding
from engineering_influence.services.interfaces.canon_finding_parser_interface import (
    CanonFindingParserInterface,
)


class CanonFindingParser(CanonFindingParserInterface):
    """A finding line starts at the line's first word, which is its severity; the rule is in square brackets. Lines
    in any other shape are not findings, so a check's progress messages do not turn into errors."""

    LINE: ClassVar[re.Pattern[str]] = re.compile(
        r"^(ERROR|WARN)\s+(.+?):\s+\[([^\]]+)\]\s+(.+?)\s*$"
    )

    def parse(self, output: str) -> tuple[CanonFinding, ...]:
        findings: list[CanonFinding] = []
        for line in output.splitlines():
            match = self.LINE.match(line.strip())
            if match is not None:
                severity, where, rule, message = match.groups()
                findings.append(CanonFinding(severity, where, rule, message))
        return tuple(findings)
