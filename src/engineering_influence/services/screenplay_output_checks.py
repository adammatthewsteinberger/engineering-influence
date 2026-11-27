# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Checks each screenplay stage's answer before it is stored, with the mechanical checks of prompt 08."""

from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.stage_output_check_interface import StageOutputCheckInterface
from engineering_influence.services.screenplay_anchors_check import ScreenplayAnchorsCheck
from engineering_influence.services.screenplay_audit_check import ScreenplayAuditCheck
from engineering_influence.services.screenplay_beat_sheet_check import ScreenplayBeatSheetCheck
from engineering_influence.services.screenplay_scene_cards_check import ScreenplaySceneCardsCheck
from engineering_influence.services.screenplay_tone_ratio_check import ScreenplayToneRatioCheck
from engineering_influence.services.screenplay_visual_grammar_check import (
    ScreenplayVisualGrammarCheck,
)


class ScreenplayOutputChecks(StageOutputCheckInterface):
    """The anchors, the audit, the beat sheet, the scene cards and the visual grammar are each checked; the brief is not,
    since it is prose. A stage
    whose answer breaks a check raises `STAGE_OUTPUT_INVALID` naming up to five problems."""

    MAX_PROBLEMS_SHOWN: ClassVar[int] = 5
    DEFAULT_TARGET_PAGES: ClassVar[int] = 180

    def __init__(self, target_pages: int = DEFAULT_TARGET_PAGES) -> None:
        self._target_pages = target_pages

    def check(self, stage: str, text: str, target_words: int | None) -> None:
        """Return when the stage's answer is usable; raise when a mechanical check finds a problem."""
        problems = self._problems(stage, text)
        if problems:
            shown = "; ".join(problems[: self.MAX_PROBLEMS_SHOWN])
            raise ApplicationError(
                code="STAGE_OUTPUT_INVALID",
                message=f"{stage}: {shown}",
                http_status=422,
            )

    def _problems(self, stage: str, text: str) -> tuple[str, ...]:
        if stage == "anchors":
            return ScreenplayAnchorsCheck().problems(text)
        if stage == "beats":
            return ScreenplayBeatSheetCheck(self._target_pages).problems(text)
        if stage == "scene_cards":
            return ScreenplaySceneCardsCheck().problems(text) + ScreenplayToneRatioCheck().problems(
                text
            )
        if stage == "audit":
            return ScreenplayAuditCheck().problems(text)
        if stage == "visual_grammar":
            return ScreenplayVisualGrammarCheck().problems(text)
        return ()
