# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Prompt 09's format test, applied mechanically to a Fountain script."""

import re
from typing import ClassVar

from engineering_influence.models.fountain_block import FountainBlock
from engineering_influence.services.interfaces.fountain_format_check_interface import (
    FountainFormatCheckInterface,
)
from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)


class FountainFormatCheck(FountainFormatCheckInterface):
    """What it refuses: a script that does not open with FADE IN: and close with FADE OUT. and THE END; a scene
    whose time of day is not on the allowed list; a camera direction in action (INSERT is allowed); digits in
    dialogue (numbers are spelled out); a parenthetical that does not lead into dialogue; parentheticals on more than
    `MAX_PARENTHETICAL_RATIO` of the speeches; more than `MAX_BEAT_PARENTHETICALS` (beat) parentheticals, since a pause
    belongs in the action; a year in a scene heading instead of (FLASHBACK).

    Interior thought in action is a note, not a problem: a reader should look at it, but it does not fail the script.
    """

    ALLOWED_TIMES: ClassVar[frozenset[str]] = frozenset(
        {"DAY", "NIGHT", "DAWN", "DUSK", "CONTINUOUS", "LATER", "SAME"}
    )
    MAX_PARENTHETICAL_RATIO: ClassVar[float] = 0.10
    MIN_SPEECHES_FOR_RATIO: ClassVar[int] = 10
    # A pause is written in the action, not as a (beat) parenthetical. Zero is the rule; a count is kept so a
    # different policy is one constant away, and the message always says how many were found.
    MAX_BEAT_PARENTHETICALS: ClassVar[int] = 0
    BEAT: ClassVar[re.Pattern[str]] = re.compile(r"\(?\s*beat\s*\)?", re.IGNORECASE)
    CAMERA: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(CLOSE ON|CLOSE UP|POV|ANGLE ON|TRACKING SHOT|DOLLY IN|DOLLY OUT|PAN TO)\b"
    )
    YEAR_IN_SLUG: ClassVar[re.Pattern[str]] = re.compile(r"\((?:19|20)\d\d\)")
    DIGIT: ClassVar[re.Pattern[str]] = re.compile(r"\d")
    INTERIORITY: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(knows|realizes|realises|feels|remembers|as if|for the rest of the film)\b",
        re.IGNORECASE,
    )

    def __init__(
        self, parser: FountainParserInterface, allowed_times: frozenset[str] = ALLOWED_TIMES
    ) -> None:
        self._parser = parser
        self._allowed_times = allowed_times

    def problems(self, text: str) -> tuple[str, ...]:
        """Every format rule the script breaks."""
        blocks = self._parser.blocks(text)
        found: list[str] = []
        if not blocks or blocks[0].kind != "transition" or blocks[0].text() != "FADE IN:":
            found.append("the script must open with FADE IN:")
        if len(blocks) < 2 or blocks[-2].text() != "FADE OUT." or blocks[-1].text() != "THE END":
            found.append("the script must close with FADE OUT. and then THE END")
        for scene in self._parser.scenes(text):
            found.extend(self._scene_problems(scene.number, scene.heading))
        for index, block in enumerate(blocks):
            if block.kind == "action":
                found.extend(
                    f"camera direction {m.group(0)!r} in action: {line}"
                    for line in block.lines
                    for m in self.CAMERA.finditer(line)
                )
            if block.kind == "dialogue" and self.DIGIT.search(block.text()):
                found.append(f"digits in dialogue, spell the number out: {block.text()[:60]!r}")
            if block.kind == "parenthetical" and not (
                index + 1 < len(blocks) and blocks[index + 1].kind == "dialogue"
            ):
                found.append(f"a parenthetical must lead into dialogue: {block.text()!r}")
        found.extend(self._ratio_problems(blocks))
        beats = sum(
            1
            for block in blocks
            if block.kind == "parenthetical" and self.BEAT.fullmatch(block.text().strip())
        )
        if beats > self.MAX_BEAT_PARENTHETICALS:
            found.append(
                f"{beats} (beat) parentheticals: a pause belongs in the action, not in parentheses"
            )
        return tuple(found)

    def notes(self, text: str) -> tuple[str, ...]:
        """Interior thought in action, for a reader to look at."""
        return tuple(
            f"interior thought in action: {line!r}"
            for block in self._parser.blocks(text)
            if block.kind == "action"
            for line in block.lines
            if self.INTERIORITY.search(line)
        )

    def _scene_problems(self, number: int, heading: str) -> list[str]:
        found: list[str] = []
        if self.YEAR_IN_SLUG.search(heading):
            found.append(f"scene {number}: use (FLASHBACK), not a year, in the heading {heading!r}")
        if " - " not in heading:
            found.append(f"scene {number}: the heading {heading!r} has no time of day after ' - '")
        else:
            time = heading.rsplit(" - ", 1)[1].strip()
            if time not in self._allowed_times:
                allowed = ", ".join(sorted(self._allowed_times))
                found.append(f"scene {number}: time {time!r} is not one of {allowed}")
        return found

    def _ratio_problems(self, blocks: tuple[FountainBlock, ...]) -> list[str]:
        dialogue = sum(1 for block in blocks if block.kind == "dialogue")
        parentheticals = sum(1 for block in blocks if block.kind == "parenthetical")
        if (
            dialogue >= self.MIN_SPEECHES_FOR_RATIO
            and parentheticals / dialogue > self.MAX_PARENTHETICAL_RATIO
        ):
            limit = f"{self.MAX_PARENTHETICAL_RATIO:.0%}"
            message = f"{parentheticals} parentheticals on {dialogue} speeches is over {limit}"
            return [f"{message}; keep them for what the actor cannot show"]
        return []
