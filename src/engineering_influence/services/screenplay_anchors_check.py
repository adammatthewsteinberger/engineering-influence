# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The anchors document's mechanical checks: its sections are present, the spine is one sentence, the images show
rather than think, All Is Lost says what is lost and why, and a structural mode is named."""

import re
from typing import ClassVar

from engineering_influence.services.interfaces.screenplay_anchors_check_interface import (
    ScreenplayAnchorsCheckInterface,
)


class ScreenplayAnchorsCheck(ScreenplayAnchorsCheckInterface):
    """Each section is a `## Heading` with the names in `SECTIONS`. Thought verbs and V.O. in the opening and closing
    images are refused, since prompt 08 asks for what can be seen and heard only. The judgement that the spine is a
    central action rather than a theme, and that the images mirror each other, stays with a reader."""

    SECTIONS: ClassVar[tuple[str, ...]] = (
        "Dramatic spine",
        "Opening image",
        "Closing image",
        "All Is Lost",
        "Cannot lose",
        "Can lose",
        "Structural mode",
    )
    MODES: ClassVar[tuple[str, ...]] = ("Jackson", "Kubrick", "Coppola")
    THOUGHT: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:thinks|knows|realizes|realises|feels|remembers)\b|\bV\.O\.", re.IGNORECASE
    )
    SENTENCE_END: ClassVar[re.Pattern[str]] = re.compile(r"(?<=[.!?])\s+")

    def problems(self, text: str) -> tuple[str, ...]:
        """Every missing section and broken rule."""
        sections = self._sections(text)
        found = [
            f"the anchors need a '## {name}' section"
            for name in self.SECTIONS
            if name not in sections
        ]
        spine = [
            part
            for part in self.SENTENCE_END.split(sections.get("Dramatic spine", "").strip())
            if part
        ]
        if "Dramatic spine" in sections and len(spine) != 1:
            found.append("the dramatic spine is one sentence in present tense")
        for name in ("Opening image", "Closing image"):
            if name in sections and self.THOUGHT.search(sections[name]):
                found.append(
                    f"the {name.lower()} shows only what can be seen and heard; it has thought or V.O."
                )
        if "Structural mode" in sections and not any(
            m in sections["Structural mode"] for m in self.MODES
        ):
            found.append("the structural mode names Jackson, Kubrick or Coppola")
        all_is_lost = sections.get("All Is Lost", "")
        says_why = "why" in all_is_lost or "because" in all_is_lost
        if "All Is Lost" in sections and not ("lost" in all_is_lost and says_why):
            found.append("All Is Lost says what is lost and why")
        return tuple(found)

    @staticmethod
    def _sections(text: str) -> dict[str, str]:
        """Each `## Heading` mapped to the text under it, up to the next heading."""
        sections: dict[str, str] = {}
        current: str | None = None
        for line in text.splitlines():
            if line.startswith("## "):
                current = line[3:].strip()
                sections[current] = ""
            elif current is not None:
                sections[current] = f"{sections[current]}{line}\n"
        return sections
