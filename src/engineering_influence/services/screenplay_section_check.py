# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Checks one drafted scene: it is exactly one scene, and it follows the format rules that apply to a scene alone."""

from engineering_influence.services.fountain_format_check import FountainFormatCheck
from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)
from engineering_influence.services.interfaces.screenplay_section_check_interface import (
    ScreenplaySectionCheckInterface,
)


class ScreenplaySectionCheck(ScreenplaySectionCheckInterface):
    """A scene is checked inside a minimal script (FADE IN: and the close added around it), so the same rules apply as
    to a whole script, except the ones that only a whole script can break (the title page and the opening)."""

    FRAME_OPEN = "FADE IN:\n\n"
    FRAME_CLOSE = "\n\nFADE OUT.\n\n>THE END<\n"

    def __init__(self, parser: FountainParserInterface) -> None:
        """Remember the Fountain parser the section is checked with."""
        self._parser = parser
        self._format = FountainFormatCheck(parser)

    def problems(self, section: str) -> tuple[str, ...]:
        """The scene's problems: a count of scene headings other than one, then the format rules."""
        scenes = self._parser.scenes(section)
        if len(scenes) != 1:
            return (f"a section is one scene; it has {len(scenes)} scene headings",)
        framed = f"{self.FRAME_OPEN}{section.strip()}{self.FRAME_CLOSE}"
        return self._format.problems(framed)
