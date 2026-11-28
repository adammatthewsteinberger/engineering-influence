# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Joins drafted scenes into one Fountain script: the title page, the scenes in order, then the close."""

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)
from engineering_influence.services.interfaces.screenplay_assembler_interface import (
    ScreenplayAssemblerInterface,
)


class ScreenplayAssembler(ScreenplayAssemblerInterface):
    """Each scene must be exactly one scene, so the assembled script has as many scenes as the cards did. The title
    page must name the title. Continuation lines of a title-page value are indented, as Fountain reads them."""

    def __init__(self, parser: FountainParserInterface) -> None:
        self._parser = parser

    def assemble(self, title_page: tuple[tuple[str, str], ...], scenes: tuple[str, ...]) -> str:
        """The script, with FADE IN: first and FADE OUT. then THE END last."""
        if not any(key == "Title" for key, _ in title_page):
            raise ApplicationError(
                code="SCREENPLAY_NO_TITLE",
                message="the title page must name the title",
                http_status=422,
            )
        if not scenes:
            raise ApplicationError(
                code="SCREENPLAY_NO_SCENES",
                message="a screenplay has at least one scene",
                http_status=422,
            )
        for index, scene in enumerate(scenes, 1):
            if len(self._parser.scenes(scene)) != 1:
                raise ApplicationError(
                    code="SCREENPLAY_SCENE_INVALID",
                    message=f"scene {index} must be exactly one scene heading and its elements",
                    http_status=422,
                )
        page = "\n".join(f"{key}: {self._value(value)}" for key, value in title_page)
        body = "\n\n".join(scene.strip() for scene in scenes)
        return f"{page}\n\nFADE IN:\n\n{body}\n\nFADE OUT.\n\n>THE END<\n"

    @staticmethod
    def _value(value: str) -> str:
        """A multi-line value keeps its lines, each continuation indented."""
        first, *rest = value.split("\n")
        return "\n".join([first, *(f"   {line}" for line in rest)])
