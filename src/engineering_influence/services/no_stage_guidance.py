# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Guidance for a run that named no skill lock: none."""

from engineering_influence.interfaces.stage_guidance_interface import StageGuidanceInterface
from engineering_influence.models.guidance import Guidance


class NoStageGuidance(StageGuidanceInterface):
    """Adds nothing to any stage, so a run without ``EI_SKILL_LOCK`` is the run it always was."""

    def for_stage(self, stage: str) -> Guidance:
        """Empty guidance."""
        return Guidance()
