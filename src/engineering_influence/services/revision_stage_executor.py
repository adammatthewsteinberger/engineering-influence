# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs one editing pass over every chapter of a drafted book."""

import asyncio
from collections.abc import Callable

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.prompt_library_interface import PromptLibraryInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.interfaces.stage_guidance_interface import StageGuidanceInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.chapter_outline import ChapterOutline
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.outline import Outline
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.revision_pass import RevisionPass
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)
from engineering_influence.services.interfaces.run_tool_loop_interface import (
    RunToolLoopInterface,
)
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface


class RevisionStageExecutor(StageExecutorInterface):
    """One pass (structure, lines or copy): each chapter is read, revised by one call with no tools, and stored.

    A chapter is done when its output file exists, so a stage that fails or is delivered twice goes back over
    the chapters and revises only the ones that are not done; a repeated call is replayed from the journal, so
    even redoing one costs nothing. Every call reserves against the run's budget through one spend guard started
    for this execution, and the skills enabled for the stage are added to the prompt as for every other
    model stage.

    **A revision is kept only if it is plausible.** A model that was asked for an edit sometimes returns a few
    lines, an essay about the chapter, or nothing. An answer that did not finish stops the stage
    (``STAGE_ANSWER_UNUSABLE``), as in drafting. An answer that did finish but is blank, or whose length in
    words is not within the pass's bounds of the chapter's, is **not stored: the chapter passes through
    unchanged**, because a retry would replay the same answer. The stage's report says which chapters came back
    unchanged, as a tolerated issue, worked out from the stored files so it survives a redelivery, and the
    stage's own artifact, ``<stage>.md``, lists every chapter's length before and after.

    The prompt is filled from what the pass names (see ``RevisionPass``). A chapter whose prompt, estimated at three
    characters a token, would not leave room for the answer in the model's window stops the stage before the call
    with the numbers; nothing is cut to make it fit.
    """

    TOKENS_PER_WORD = 1.6
    OUTPUT_ROOM = 400
    INPUT_MARGIN = 512
    CHARACTERS_PER_TOKEN = 3

    def __init__(
        self,
        revision: RevisionPass,
        artifacts: ArtifactStoreInterface,
        prompts: PromptLibraryInterface,
        outlines: OutlineParserInterface,
        loop: RunToolLoopInterface,
        guidance: StageGuidanceInterface,
        guards: Callable[[Budget], SpendGuardInterface],
        context_window: int,
        max_output_tokens: int,
    ) -> None:
        if context_window < 1 or max_output_tokens < 1:
            raise ValueError("a model has a window and an output limit")
        self._pass = revision
        self._artifacts = artifacts
        self._prompts = prompts
        self._outlines = outlines
        self._loop = loop
        self._guidance = guidance
        self._guards = guards
        self._window = context_window
        self._max_output = max_output_tokens

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Revise the chapters that are not done, then write the list."""
        outline_text, voice = await self._opening(run)
        outline = self._outlines.parse(outline_text)
        sources = await self._sources(run, outline)
        summaries = await self._summaries(run, outline)
        guard = self._guards(run.budget)
        for chapter in outline.chapters:
            if await self._read(run, self._name(self._pass.output, chapter.number)) is None:
                source = sources[chapter.number]
                values = {
                    "voice": voice,
                    "outline": outline_text,
                    "summaries": self._others(summaries, chapter.number),
                    "beats": chapter.render(),
                    "chapter": source,
                }
                request = self._request(run, source, values)
                outcome = await asyncio.to_thread(
                    self._loop.run, guard, run.run_id, run.stage, attempt, request
                )
                if not outcome.complete:
                    # An unfinished answer always carries the reasons (see ToolLoopResult).
                    why = "; ".join(f"{i.code}: {i.detail}" for i in outcome.issues)
                    raise self._unusable(chapter.number, why)
                kept = outcome.text if self._plausible(source, outcome.text) else source
                await self._store(run, self._name(self._pass.output, chapter.number), kept)
        return await self._report(run, outline, sources)

    async def _opening(self, run: BookRun) -> tuple[str, str]:
        wanted = ["outline.md"] + (["positioning.md"] if "voice" in self._pass.blanks else [])
        texts = {name: await self._read(run, name) for name in wanted}
        missing = [name for name, text in texts.items() if text is None]
        if missing:
            raise self._missing(run, missing)
        return texts["outline.md"] or "", texts.get("positioning.md") or ""

    async def _sources(self, run: BookRun, outline: Outline) -> dict[int, str]:
        texts = {
            chapter.number: await self._read(run, self._name(self._pass.source, chapter.number))
            for chapter in outline.chapters
        }
        missing = [
            self._name(self._pass.source, number) for number, text in texts.items() if text is None
        ]
        if missing:
            raise self._missing(run, missing)
        return {number: text or "" for number, text in texts.items()}

    async def _summaries(self, run: BookRun, outline: Outline) -> dict[int, str]:
        if "summaries" not in self._pass.blanks:
            return {}
        texts = {
            chapter.number: await self._read(run, self._name("summary", chapter.number))
            for chapter in outline.chapters
        }
        missing = [self._name("summary", number) for number, text in texts.items() if text is None]
        if missing:
            raise self._missing(run, missing)
        return {number: " ".join((text or "").split()) for number, text in texts.items()}

    @staticmethod
    def _others(summaries: dict[int, str], number: int) -> str:
        return "\n".join(f"Chapter {n}: {text}" for n, text in summaries.items() if n != number)

    def _request(self, run: BookRun, source: str, values: dict[str, str]) -> ModelRequest:
        template = self._prompts.get(self._pass.template)
        guidance = self._guidance.for_stage(run.stage)
        system = template.render("system")
        prompt = template.render("user", {name: values[name] for name in self._pass.blanks})
        version = template.identifier()
        if not guidance.empty():
            prompt = f"{prompt}\n\n{guidance.text}"
            version = f"{version}+{guidance.identity}"
        words = len(source.split())
        output_cap = min(
            int(words * self.TOKENS_PER_WORD * self._pass.max_ratio) + self.OUTPUT_ROOM,
            self._max_output,
        )
        needed = (len(system) + len(prompt)) // self.CHARACTERS_PER_TOKEN + 1
        room = self._window - output_cap - self.INPUT_MARGIN
        if needed > room:
            raise ApplicationError(
                code="STAGE_MODEL_TOO_SMALL",
                message=(
                    f"{run.stage}: the model's window of {self._window} tokens leaves {max(room, 0)} for the "
                    f"prompt after room for a {output_cap} token answer, and this chapter's prompt is about "
                    f"{needed}; use a model with a larger window"
                ),
                http_status=422,
            )
        return ModelRequest(
            system=system, prompt=prompt, max_output_tokens=output_cap, prompt_version=version
        )

    def _plausible(self, source: str, answer: str) -> bool:
        before, after = len(source.split()), len(answer.split())
        return self._pass.min_ratio * before <= after <= self._pass.max_ratio * before

    async def _report(self, run: BookRun, outline: Outline, sources: dict[int, str]) -> StageReport:
        lines = [f"# Revision: {self._pass.stage}", ""]
        issues = []
        for chapter in outline.chapters:
            revised = await self._read(run, self._name(self._pass.output, chapter.number)) or ""
            before, after = len(sources[chapter.number].split()), len(revised.split())
            unchanged = revised == sources[chapter.number]
            lines.append(
                f"- {chapter.heading()} ({before:,} to {after:,} words"
                + (", unchanged)" if unchanged else ")")
            )
            if unchanged:
                issues.append(self._unchanged(run, chapter))
        await self._store(run, f"{self._pass.stage}.md", "\n".join(lines) + "\n")
        return StageReport(tuple(issues))

    @staticmethod
    def _unchanged(run: BookRun, chapter: ChapterOutline) -> QualityIssue:
        return QualityIssue(
            run.stage,
            "revision-unchanged",
            f"chapter {chapter.number} came back from {run.stage} unchanged",
            blocking=False,
        )

    def _unusable(self, number: int, why: str) -> ApplicationError:
        return ApplicationError(
            code="STAGE_ANSWER_UNUSABLE",
            message=f"{self._pass.stage}: chapter {number}: {why}",
            http_status=502,
        )

    @staticmethod
    def _missing(run: BookRun, names: list[str]) -> ApplicationError:
        return ApplicationError(
            code="STAGE_INPUT_MISSING",
            message=f"stage {run.stage!r} needs {', '.join(names)}, which this run has not stored",
            http_status=409,
        )

    @staticmethod
    def _name(prefix: str, number: int) -> str:
        return f"{prefix}_{number:02d}.md"

    async def _read(self, run: BookRun, name: str) -> str | None:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
        return None if data is None else data.decode("utf-8")

    async def _store(self, run: BookRun, name: str, text: str) -> None:
        await asyncio.to_thread(self._artifacts.put, run.run_id, name, text.encode("utf-8"))
