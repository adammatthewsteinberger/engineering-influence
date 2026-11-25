# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs one editing pass over every chapter of a drafted book."""

import asyncio
from collections.abc import Callable

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.spend_consent_needed_error import SpendConsentNeededError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.prompt_library_interface import PromptLibraryInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.interfaces.stage_guidance_interface import StageGuidanceInterface
from engineering_influence.interfaces.tool_registry_interface import ToolRegistryInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.chapter_outline import ChapterOutline
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.outline import Outline
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.revision_pass import RevisionPass
from engineering_influence.models.stage_report import StageReport
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_loop_result import ToolLoopResult
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
    unchanged**. The prompt says how long the chapter is and what range to stay in, because a model asked to edit a
    chapter in one call otherwise tends to summarise it. An answer that is still rejected is asked for once more, with
    its length and the range in the prompt, which makes it a different request and so not a replay of the first; if that
    one does not finish, the first answer's rejection stands. Each such rejection is a tolerated
    ``revision-rejected`` issue that gives the answer's length and the bounds it missed, and is recorded in
    ``<stage>_rejected_NN.md`` for each chapter. A chapter whose answer was plausible but identical to its source is a tolerated
    ``revision-unchanged`` issue. Both are worked out from the stored files so a redelivery reports the same,
    and the stage's own artifact, ``<stage>.md``, lists every chapter's length before and after.

    **A long chapter is revised in parts.** A chapter above ``MAX_CALL_WORDS`` (4,000) is cut at its blank lines into
    parts no longer than that, and each part is one call with its own length bounds, so no answer has to fit more words
    than the model can write in one reply. Most chapters are one part and are unaffected. A part whose answer is
    implausible keeps its own text, and the report counts the rejected parts. The structure pass therefore reorders and
    cuts only within a part; material does not move between parts.

    **A revision is optional, so a pass that runs out of money does not stop the run.** When a call would pass the
    cap, that chapter and every later one in the pass keep the text they had (it is stored unchanged, so the next pass
    reads it as usual; the chapter it stopped at is kept in ``<stage>_skipped.md`` so a redelivery reports the same), the
    stage's list says so, and one tolerated issue (``revision-skipped-budget``) records it in
    the quality report. Nothing is sent and nothing is paid for the chapters that were skipped. The drafting stages are
    different: a book cannot be finished without them, so they still stop and ask for the money.

    The prompt is filled from what the pass names (see ``RevisionPass``). A chapter whose prompt, estimated at three
    characters a token, would not leave room for the answer in the model's window stops the stage before the call
    with the numbers; nothing is cut to make it fit.
    """

    MAX_CALL_WORDS = 4_000
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
        tools: ToolRegistryInterface,
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
        self._tools = tools

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Revise the chapters that are not done, then write the list."""
        outline_text, voice = await self._opening(run)
        outline = self._outlines.parse(outline_text)
        sources = await self._sources(run, outline)
        summaries = await self._summaries(run, outline)
        guard = self._guards(run.budget)
        first_skipped = await self._first_skipped(run)
        for chapter in outline.chapters:
            if await self._read(run, self._name(self._pass.output, chapter.number)) is None:
                source = sources[chapter.number]
                if first_skipped is not None and chapter.number >= first_skipped:
                    # The money ran out earlier in this pass: nothing more is asked of the model.
                    await self._store(run, self._name(self._pass.output, chapter.number), source)
                    continue
                base = {
                    "voice": voice,
                    "outline": outline_text,
                    "summaries": self._others(summaries, chapter.number),
                    "beats": chapter.render(),
                }
                try:
                    kept, rejected = await self._revise(guard, run, attempt, chapter, source, base)
                except SpendConsentNeededError:
                    # Recorded first, so a redelivery after this knows where the pass stopped and reports the same list.
                    first_skipped = chapter.number
                    await self._store(run, f"{self._pass.stage}_skipped.md", str(first_skipped))
                    await self._store(run, self._name(self._pass.output, chapter.number), source)
                    continue
                if rejected:
                    # Recorded before the chapter is stored, so a redelivery reports the same rejection.
                    await self._reject(run, chapter.number, rejected)
                await self._store(run, self._name(self._pass.output, chapter.number), kept)
        return await self._report(run, outline, sources, first_skipped)

    async def _revise(
        self,
        guard: SpendGuardInterface,
        run: BookRun,
        attempt: int,
        chapter: ChapterOutline,
        source: str,
        base: dict[str, str],
    ) -> tuple[str, int]:
        """The chapter revised part by part, and how many parts kept their source because the answer was implausible.

        A chapter of up to ``MAX_CALL_WORDS`` is one part, so most chapters are one call as before. A longer chapter is
        cut at its paragraph breaks into parts no longer than that, each revised in its own call, so no answer has to fit
        more than the model's reply can carry. The parts are joined with the blank lines they were cut at.
        """
        kept: list[str] = []
        rejected = 0
        for part in self._parts(source):
            values = {**base, "chapter": part, **self._length(part)}
            answer = await self._part(guard, run, attempt, chapter, part, values)
            if answer is None:
                rejected += 1
                kept.append(part)
            else:
                kept.append(answer)
        return "\n\n".join(kept), rejected

    async def _part(
        self,
        guard: SpendGuardInterface,
        run: BookRun,
        attempt: int,
        chapter: ChapterOutline,
        part: str,
        values: dict[str, str],
    ) -> str | None:
        """One part's revision, or None when the answer is implausible and the part keeps its text."""
        outcome = await self._ask(guard, run, attempt, self._request(run, part, values))
        if outcome.complete and not self._plausible(part, outcome.text):
            # What was wrong goes in the prompt, so this is a new request and not a replay of the first.
            again = await self._ask(
                guard,
                run,
                attempt,
                self._request(run, part, values, len(outcome.text.split())),
            )
            outcome = again if again.complete else outcome
        if not outcome.complete:
            # An unfinished answer always carries the reasons (see ToolLoopResult).
            why = "; ".join(f"{i.code}: {i.detail}" for i in outcome.issues)
            raise self._unusable(chapter.number, why)
        return outcome.text if self._plausible(part, outcome.text) else None

    def _parts(self, source: str) -> tuple[str, ...]:
        """The chapter cut at its blank lines into parts of at most ``MAX_CALL_WORDS`` words, or one part when it fits."""
        parts: list[str] = []
        current: list[str] = []
        words = 0
        for paragraph in source.split("\n\n"):
            count = len(paragraph.split())
            if current and words + count > self.MAX_CALL_WORDS:
                parts.append("\n\n".join(current))
                current, words = [], 0
            current.append(paragraph)
            words += count
        parts.append("\n\n".join(current))
        return tuple(parts)

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

    async def _ask(
        self, guard: SpendGuardInterface, run: BookRun, attempt: int, request: ModelRequest
    ) -> ToolLoopResult:
        return await asyncio.to_thread(
            self._loop.run, guard, run.run_id, run.stage, attempt, request
        )

    def _length(self, source: str) -> dict[str, str]:
        """The chapter's length and the range the model is asked to stay in, halfway to each bound the pass enforces."""
        words = len(source.split())
        floor = round(words * (1 + self._pass.min_ratio) / 2)
        ceiling = round(words * (1 + self._pass.max_ratio) / 2)
        return {"words": f"{words:,}", "floor": f"{floor:,}", "ceiling": f"{ceiling:,}"}

    def _request(
        self, run: BookRun, source: str, values: dict[str, str], rejected: int | None = None
    ) -> ModelRequest:
        template = self._prompts.get(self._pass.template)
        guidance = self._guidance.for_stage(run.stage)
        system = template.render("system")
        prompt = template.render("user", {name: values[name] for name in self._pass.blanks})
        if rejected is not None:
            retry = {name: values[name] for name in ("words", "floor", "ceiling")}
            prompt = f"{prompt}\n\n{template.render('retry', {'answer': f'{rejected:,}', **retry})}"
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
            system=system,
            prompt=prompt,
            max_output_tokens=output_cap,
            prompt_version=version,
            tools=self._offered(guidance.tools),
        )

    def _offered(self, names: tuple[str, ...]) -> tuple[ToolDefinition, ...]:
        try:
            return self._tools.definitions(names)
        except ValueError as error:
            raise ApplicationError(
                code="STAGE_TOOL_UNKNOWN", message=str(error), http_status=500
            ) from error

    def _plausible(self, source: str, answer: str) -> bool:
        before, after = len(source.split()), len(answer.split())
        return self._pass.min_ratio * before <= after <= self._pass.max_ratio * before

    async def _report(
        self, run: BookRun, outline: Outline, sources: dict[int, str], first_skipped: int | None
    ) -> StageReport:
        lines = [f"# Revision: {self._pass.stage}", ""]
        issues = []
        rejected = await self._rejected(run, outline)
        for chapter in outline.chapters:
            number = chapter.number
            revised = await self._read(run, self._name(self._pass.output, number)) or ""
            before, after = len(sources[number].split()), len(revised.split())
            parts = len(self._parts(sources[number]))
            if self._was_skipped(number, first_skipped):
                note = ", not revised: out of budget"
            elif number in rejected:
                note = f", {rejected[number]} of {parts} parts rejected, kept as they were"
                issues.append(self._rejected_issue(run, chapter, rejected[number], parts))
            elif revised == sources[number]:
                note = ", unchanged"
                issues.append(self._unchanged(run, chapter))
            else:
                note = ""
            lines.append(f"- {chapter.heading()} ({before:,} to {after:,} words{note})")
        if first_skipped is not None:
            issues.append(
                QualityIssue(
                    run.stage,
                    "revision-skipped-budget",
                    f"{run.stage} ran out of budget: chapters {first_skipped} to {outline.chapters[-1].number} "
                    "keep the text they had",
                    blocking=False,
                )
            )
        await self._store(run, f"{self._pass.stage}.md", "\n".join(lines) + "\n")
        return StageReport(tuple(issues))

    @staticmethod
    def _was_skipped(number: int, first_skipped: int | None) -> bool:
        return first_skipped is not None and number >= first_skipped

    async def _first_skipped(self, run: BookRun) -> int | None:
        marker = await self._read(run, f"{self._pass.stage}_skipped.md")
        return None if marker is None else int(marker)

    async def _reject(self, run: BookRun, number: int, parts: int) -> None:
        # One file per chapter: run artifacts are written once, so a shared list could not be extended.
        await self._store(run, self._rejection_name(number), f"{parts}\n")

    async def _rejected(self, run: BookRun, outline: Outline) -> dict[int, int]:
        found = {}
        for chapter in outline.chapters:
            text = await self._read(run, self._rejection_name(chapter.number))
            if text is not None:
                found[chapter.number] = int(text)
        return found

    def _rejection_name(self, number: int) -> str:
        return self._name(f"{self._pass.stage}_rejected", number)

    def _rejected_issue(
        self, run: BookRun, chapter: ChapterOutline, parts: int, of: int
    ) -> QualityIssue:
        return QualityIssue(
            run.stage,
            "revision-rejected",
            f"chapter {chapter.number}: {parts} of {of} parts of the answer from {run.stage} fell outside the "
            "bounds the chapter allows, so those parts were kept as they were",
            blocking=False,
        )

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
