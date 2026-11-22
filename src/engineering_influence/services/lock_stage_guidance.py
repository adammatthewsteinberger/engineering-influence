# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The text of the skills a lock enables for a stage, framed for a prompt."""

import hashlib
import re
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.stage_guidance_interface import StageGuidanceInterface
from engineering_influence.models.guidance import Guidance
from engineering_influence.models.prompt_template import PromptTemplate
from engineering_influence.models.skill import Skill
from engineering_influence.models.skill_lock import SkillLock


class LockStageGuidance(StageGuidanceInterface):
    """What the lock enables for a stage, and nothing else.

    A stage the lock does not name for any skill gets empty guidance, so a skill that is merely
    installed reaches no prompt. Each skill's text for the stage goes in its own
    ``<skill name="..." version="...">`` block, in name order, inside the frame from the
    ``skill_guidance`` template. A copy of one of the block tags inside a skill's text is defused
    first, so a skill cannot close its block or open a second frame. Nothing here can add a tool, run
    anything or widen what a stage may call: the result is text for the end of one prompt.

    ``identity`` names the frame (its template and version) and the exact skills (name, version
    and hash) that made the text, which is what a journal key needs to tell one prompt from another.
    """

    TAG: ClassVar[re.Pattern[str]] = re.compile(
        r"<\s*(/?)\s*(skill|installed_guidance)", re.IGNORECASE
    )

    def __init__(
        self, lock: SkillLock, skills: tuple[Skill, ...], template: PromptTemplate
    ) -> None:
        self._lock = lock
        self._skills = {skill.name: skill for skill in skills}
        self._template = template

    def for_stage(self, stage: str) -> Guidance:
        """The text and identity to add for the stage; empty guidance when no skill is enabled for it."""
        entries = self._lock.enabled(stage)
        blocks = []
        for entry in entries:
            skill = self._skills.get(entry.name)
            text = skill.part(stage) if skill is not None else None
            if skill is None or skill.version != entry.version or text is None:
                raise ApplicationError(
                    code="SKILL_LOCK_MISMATCH",
                    message=f"skill {entry.name!r} was not loaded as the lock describes it",
                    http_status=503,
                )
            blocks.append(
                f'<skill name="{skill.name}" version="{skill.version}">\n'
                f"{self._defused(text)}\n</skill>"
            )
        if not blocks:
            return Guidance()
        framed = self._template.render("frame", {"skills": "\n\n".join(blocks)})
        named = "\n".join(entry.identity() for entry in entries)
        digest = hashlib.sha256(named.encode("utf-8")).hexdigest()[:16]
        return Guidance(framed, f"{self._template.identifier()}:{digest}")

    def _defused(self, text: str) -> str:
        return self.TAG.sub(lambda match: f"<\\{match.group(1)}{match.group(2)}", text)
