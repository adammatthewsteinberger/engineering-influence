# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The assembly stage of a screenplay: the revised scenes, in card order, become one script that must pass the format rules."""

import asyncio
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.fountain_format_check import FountainFormatCheck
from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)
from engineering_influence.services.interfaces.scene_card_list_interface import (
    SceneCardListInterface,
)
from engineering_influence.services.interfaces.screenplay_assembler_interface import (
    ScreenplayAssemblerInterface,
)
from engineering_influence.services.interfaces.screenplay_beat_position_check_interface import (
    ScreenplayBeatPositionCheckInterface,
)
from engineering_influence.services.interfaces.screenplay_title_parser_interface import (
    ScreenplayTitleParserInterface,
)
from engineering_influence.services.screenplay_title_parser import ScreenplayTitleParser


class ScreenplayAssembleStageExecutor(StageExecutorInterface):
    """No model call. Each card's revised scene is one scene (the assembler refuses a scene with two headings), and the
    whole script must pass the Fountain format rules, which the scenes alone cannot break: the title page, the opening
    and the close are added here. Then the beats must fall where the beat sheet puts them, measured in the script's
    length, which only the assembled script can show.

    The title page names the brief's title, or UNTITLED when the author gave none. The script is stored as
    ``screenplay.fountain``, and the stage writes no other artifact.
    """

    STAGE: ClassVar[str] = "assemble_script"
    SCRIPT: ClassVar[str] = "screenplay.fountain"
    UNTITLED: ClassVar[str] = "UNTITLED"
    MAX_PROBLEMS_SHOWN: ClassVar[int] = 5

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        cards: SceneCardListInterface,
        assembler: ScreenplayAssemblerInterface,
        parser: FountainParserInterface,
        positions: ScreenplayBeatPositionCheckInterface,
        titles: ScreenplayTitleParserInterface,
    ) -> None:
        self._artifacts = artifacts
        self._cards = cards
        self._assembler = assembler
        self._format = FountainFormatCheck(parser)
        self._positions = positions
        self._titles = titles

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Assemble the script from the revised scenes in card order, check it, and store it."""
        cards = self._cards.parse(await self._required(run, "scene_cards.md"))
        scenes = tuple([await self._required(run, card.dialogued()) for card in cards])
        script = self._assembler.assemble(await self._title_page(run), scenes)
        problems = self._format.problems(script)
        if problems:
            shown = "; ".join(problems[: self.MAX_PROBLEMS_SHOWN])
            raise ApplicationError(
                code="STAGE_OUTPUT_INVALID",
                message=f"the assembled script breaks the format rules: {shown}",
                http_status=422,
            )
        placed = self._positions.problems(
            await self._required(run, "beats.md"),
            tuple((card.beat, scene) for card, scene in zip(cards, scenes, strict=True)),
        )
        if placed:
            shown = "; ".join(placed[: self.MAX_PROBLEMS_SHOWN])
            raise ApplicationError(
                code="STAGE_OUTPUT_INVALID",
                message=f"the beats do not fall where the beat sheet puts them: {shown}",
                http_status=422,
            )
        await self._put(run, self.SCRIPT, script)
        return StageReport()

    async def _title_page(self, run: BookRun) -> tuple[tuple[str, str], ...]:
        """The title, then the credit and source the author's title.toml gives, when the run kept one."""
        entries = [("Title", run.brief.title_hint or self.UNTITLED)]
        stored = await asyncio.to_thread(
            self._artifacts.get, run.run_id, ScreenplayTitleParser.ARTIFACT
        )
        if stored is not None:
            entries.extend(self._titles.parse(stored.decode("utf-8")).entries())
        return tuple(entries)

    async def _required(self, run: BookRun, name: str) -> str:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
        if data is None:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {run.stage!r} needs {name}, which this run has not stored",
                http_status=409,
            )
        return data.decode("utf-8")

    async def _put(self, run: BookRun, name: str, text: str) -> None:
        await asyncio.to_thread(self._artifacts.put, run.run_id, name, text.encode("utf-8"))
