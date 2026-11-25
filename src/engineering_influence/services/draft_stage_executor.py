# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Drafts every chapter of the outline, in order, and keeps a summary of each for the next."""

import asyncio
from collections.abc import Callable

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.draft_checks_interface import DraftChecksInterface
from engineering_influence.interfaces.prompt_library_interface import PromptLibraryInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.interfaces.stage_guidance_interface import StageGuidanceInterface
from engineering_influence.interfaces.tool_registry_interface import ToolRegistryInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.chapter_outline import ChapterOutline
from engineering_influence.models.context_plan import ContextPlan
from engineering_influence.models.draft_recipe import DraftRecipe
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.outline import Outline
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.stage_report import StageReport
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_loop_result import ToolLoopResult
from engineering_influence.services.interfaces.context_assembler_interface import (
    ContextAssemblerInterface,
)
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)
from engineering_influence.services.interfaces.run_tool_loop_interface import (
    RunToolLoopInterface,
)
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface
from engineering_influence.services.no_draft_checks import NoDraftChecks


class DraftStageExecutor(StageExecutorInterface):
    """The ``draft`` stage: one chapter after another, each written from what came before it (ADR 0010).

    For chapter *n* the context assembler is given the voice (the brief and the positioning), the grounding
    (the whole outline and the research notes), this chapter's entry in the outline, the summaries of chapters 1
    to *n*-1 and the tail of chapter *n*-1, and fits them to the model's window. One call with no tools drafts
    the chapter and a second summarizes it. Everything from earlier stages and the web reaches the model as an
    untrusted block (see the assembler); the instruction, which is the only plain text, holds numbers and nothing
    else.

    **A chapter is done when both of its files exist** (``chapter_NN.md`` and ``summary_NN.md``). A stage that
    fails or is redelivered part-way goes back over the chapters in order and does only the work that is not
    done: a chapter that was written but not summarized is summarized from the stored text, never redrafted.
    The artifact store is write-once, and a call that is repeated with the same request is replayed from the
    journal, so even redoing a call costs nothing and returns the same words. Every call reserves against the
    run's budget through one spend guard started for this execution.

    **How long a chapter is** comes from the brief's ``target_words`` shared across the chapters (2,500 words
    when there is none, never less than 300 or more than 6,000), and the output cap is that many words as tokens
    with some room, never more than the model allows. The input budget is what is left of the model's window, less
    a margin, less an allowance for any skills enabled for this stage. If the window is too small to hold even
    the fixed parts, the stage stops before the first call with the numbers.

    The stage's own artifact is ``draft.md``, an index of the chapters and their lengths.
    """

    STAGE = "draft"
    NONFICTION = DraftRecipe(
        ("brief", "positioning", "research", "outline"),
        (("The author's brief", "brief"), ("The positioning", "positioning")),
        (("The whole outline", "outline"), ("The research notes", "research")),
        "context_pack",
        "stage_summary",
        "Write section {section} of {sections} of chapter {number} of {count} now, covering beat {section} "
        "above, in about {words} words. Write only this section.",
        sectioned=True,
    )
    NO_CHECKS = NoDraftChecks()
    REPORTED_ISSUES = 50
    CONTINUITY = "continuity.md"
    DEFAULT_WORDS = 2_500
    MIN_WORDS = 300
    MAX_WORDS = 6_000
    MAX_CHAPTER_WORDS = 12_000
    MIN_SECTION_WORDS = 150
    MAX_SECTION_WORDS = 3_000
    TOKENS_PER_WORD = 1.6
    OUTPUT_ROOM = 400
    SUMMARY_TOKENS = 400
    INPUT_MARGIN = 512
    CHARACTERS_PER_TOKEN = 3

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        prompts: PromptLibraryInterface,
        outlines: OutlineParserInterface,
        contexts: ContextAssemblerInterface,
        loop: RunToolLoopInterface,
        guidance: StageGuidanceInterface,
        guards: Callable[[Budget], SpendGuardInterface],
        context_window: int,
        max_output_tokens: int,
        tools: ToolRegistryInterface,
        recipe: DraftRecipe = NONFICTION,
        checks: DraftChecksInterface = NO_CHECKS,
    ) -> None:
        if context_window < 1 or max_output_tokens < 1:
            raise ValueError("a model has a window and an output limit")
        self._artifacts = artifacts
        self._prompts = prompts
        self._outlines = outlines
        self._contexts = contexts
        self._loop = loop
        self._guidance = guidance
        self._guards = guards
        self._window = context_window
        self._max_output = max_output_tokens
        self._tools = tools
        self._recipe = recipe
        self._checks = checks

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Draft the chapters that are not done, then write the index."""
        stored = await asyncio.to_thread(self._artifacts.names, run.run_id)
        missing = [f"{name}.md" for name in self._recipe.inputs if f"{name}.md" not in stored]
        if missing:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {run.stage!r} needs {', '.join(missing)}, which this run has not stored",
                http_status=409,
            )
        texts = {name: await self._text(run, f"{name}.md") for name in self._recipe.inputs}
        outline = self._outlines.parse(texts["outline"])
        guidance = self._guidance.for_stage(run.stage)
        words = self._words(run.brief.target_words, outline.count())
        per_call = self.MAX_SECTION_WORDS if self._recipe.sectioned else words
        output_cap = min(int(per_call * self.TOKENS_PER_WORD) + self.OUTPUT_ROOM, self._max_output)
        input_cap = (
            self._window
            - output_cap
            - self.INPUT_MARGIN
            - len(guidance.text) // self.CHARACTERS_PER_TOKEN
        )
        if input_cap < 1:
            raise ApplicationError(
                code="STAGE_MODEL_TOO_SMALL",
                message=(
                    f"the model's window of {self._window} tokens leaves no room to write "
                    f"{per_call} words ({output_cap} tokens) and read what came before; "
                    "use a model with a larger window or a smaller target"
                ),
                http_status=422,
            )
        guard = self._guards(run.budget)
        for chapter in outline.chapters:
            await self._chapter(
                run, attempt, guard, outline, chapter, texts, words, output_cap, input_cap
            )
        issues = await self._issues(run, outline, texts)
        await self._index(run, outline, issues)
        return StageReport(issues=issues[: self.REPORTED_ISSUES])

    async def _chapter(
        self,
        run: BookRun,
        attempt: int,
        guard: SpendGuardInterface,
        outline: Outline,
        chapter: ChapterOutline,
        texts: dict[str, str],
        words: int,
        output_cap: int,
        input_cap: int,
    ) -> None:
        number = chapter.number
        if await self._read(run, self._chapter_name(number)) is None:
            written = await self._written(
                run, attempt, guard, outline, chapter, texts, words, output_cap, input_cap
            )
            await self._store(run, self._chapter_name(number), written)
        written = await self._text(run, self._chapter_name(number))
        if await self._read(run, self._summary_name(number)) is None:
            outcome = await asyncio.to_thread(
                self._loop.run,
                guard,
                run.run_id,
                run.stage,
                attempt,
                self._summary_request(written),
            )
            await self._store(
                run, self._summary_name(number), self._usable(outcome, f"summary {number}")
            )

    async def _written(
        self,
        run: BookRun,
        attempt: int,
        guard: SpendGuardInterface,
        outline: Outline,
        chapter: ChapterOutline,
        texts: dict[str, str],
        words: int,
        output_cap: int,
        input_cap: int,
    ) -> str:
        """The chapter's text: one call for an unsectioned draft, else each beat's section joined under the heading."""
        if not self._recipe.sectioned:
            return await self._call(
                run,
                attempt,
                guard,
                self._draft_request(
                    run, outline, chapter, texts, words, output_cap, input_cap, 1, 1
                ),
                f"chapter {chapter.number}",
            )
        sections = len(chapter.beats)
        parts = [
            await self._section(
                run, attempt, guard, outline, chapter, section, texts, words, output_cap, input_cap
            )
            for section in range(1, sections + 1)
        ]
        return "\n\n".join([f"# {chapter.heading()}", *parts])

    async def _section(
        self,
        run: BookRun,
        attempt: int,
        guard: SpendGuardInterface,
        outline: Outline,
        chapter: ChapterOutline,
        section: int,
        texts: dict[str, str],
        words: int,
        output_cap: int,
        input_cap: int,
    ) -> str:
        """One beat's section, stored as ``chapter_NN_sKK.md`` once written, so a redelivery skips it."""
        name = self._section_name(chapter.number, section)
        written = await self._read(run, name)
        if written is not None:
            return written
        text = await self._call(
            run,
            attempt,
            guard,
            self._draft_request(
                run,
                outline,
                chapter,
                texts,
                words,
                output_cap,
                input_cap,
                section,
                len(chapter.beats),
            ),
            f"chapter {chapter.number} section {section}",
        )
        await self._store(run, name, text)
        return text

    async def _call(
        self,
        run: BookRun,
        attempt: int,
        guard: SpendGuardInterface,
        request: ModelRequest,
        what: str,
    ) -> str:
        outcome = await asyncio.to_thread(
            self._loop.run, guard, run.run_id, run.stage, attempt, request
        )
        return self._usable(outcome, what)

    def _draft_request(
        self,
        run: BookRun,
        outline: Outline,
        chapter: ChapterOutline,
        texts: dict[str, str],
        words: int,
        output_cap: int,
        input_cap: int,
        section: int,
        sections: int,
    ) -> ModelRequest:
        number = chapter.number
        summaries = tuple(
            f"Chapter {earlier}: "
            + " ".join(self._stored(run, self._summary_name(earlier)).split())
            for earlier in range(1, number)
        )
        plan = ContextPlan(
            style=self._recipe.style_text(texts),
            grounding=self._recipe.grounding_text(texts),
            beats=chapter.render(),
            instruction=self._recipe.instruction_text(
                number,
                outline.count(),
                self._section_words(words, sections) if self._recipe.sectioned else words,
                run.brief.violence or "not given",
                run.brief.heat or "not given",
                section,
                sections,
            ),
            prior_summaries=summaries,
            previous_tail=self._tail(run, number, section),
        )
        assembled = self._contexts.assemble(plan, input_cap)
        guidance = self._guidance.for_stage(run.stage)
        version = self._prompts.get(self._recipe.context_template).identifier()
        prompt = assembled.prompt
        if not guidance.empty():
            prompt = f"{prompt}\n\n{guidance.text}"
            version = f"{version}+{guidance.identity}"
        return ModelRequest(
            system=assembled.system,
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

    def _summary_request(self, chapter_text: str) -> ModelRequest:
        template = self._prompts.get(self._recipe.summary_template)
        return ModelRequest(
            system=template.render("system"),
            prompt=template.render("user", {"chapter": chapter_text}),
            max_output_tokens=self.SUMMARY_TOKENS,
            prompt_version=template.identifier(),
        )

    def _words(self, target: int | None, chapters: int) -> int:
        shared = target // chapters if target else self.DEFAULT_WORDS
        ceiling = self.MAX_CHAPTER_WORDS if self._recipe.sectioned else self.MAX_WORDS
        return max(self.MIN_WORDS, min(ceiling, shared))

    def _section_words(self, chapter_words: int, sections: int) -> int:
        """The words one section should run to: the chapter's share, kept inside one call's reach."""
        return max(self.MIN_SECTION_WORDS, min(self.MAX_SECTION_WORDS, chapter_words // sections))

    def _tail(self, run: BookRun, number: int, section: int) -> str:
        """The end of the text before this section: the section before, or the chapter before for section 1."""
        if section > 1:
            return self._stored(run, self._section_name(number, section - 1))
        return self._stored(run, self._chapter_name(number - 1)) if number > 1 else ""

    async def _issues(
        self, run: BookRun, outline: Outline, texts: dict[str, str]
    ) -> tuple[QualityIssue, ...]:
        chapters = tuple(
            [await self._text(run, self._chapter_name(item.number)) for item in outline.chapters]
        )
        found = self._checks.issues(texts, chapters)
        if found:
            lines = ["# Continuity", ""] + [f"- {item.detail}" for item in found]
            await self._store(run, self.CONTINUITY, "\n".join(lines) + "\n")
        return found

    async def _index(
        self, run: BookRun, outline: Outline, issues: tuple[QualityIssue, ...]
    ) -> None:
        lines = ["# Draft", ""]
        total = 0
        for chapter in outline.chapters:
            length = len((await self._text(run, self._chapter_name(chapter.number))).split())
            total += length
            lines.append(f"- {chapter.heading()} ({length:,} words)")
        lines += ["", f"Total: {total:,} words"]
        if issues:
            lines.append(f"Continuity: {len(issues):,} findings, in {self.CONTINUITY}")
        await self._store(run, f"{self.STAGE}.md", "\n".join(lines) + "\n")

    def _usable(self, outcome: ToolLoopResult, what: str) -> str:
        if outcome.complete and outcome.text.strip():
            return outcome.text
        why = (
            "; ".join(f"{issue.code}: {issue.detail}" for issue in outcome.issues)
            or "the model returned no text"
        )
        raise ApplicationError(
            code="STAGE_ANSWER_UNUSABLE", message=f"{self.STAGE}: {what}: {why}", http_status=502
        )

    async def _text(self, run: BookRun, name: str) -> str:
        return await self._read(run, name) or ""

    async def _read(self, run: BookRun, name: str) -> str | None:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
        return None if data is None else data.decode("utf-8")

    def _stored(self, run: BookRun, name: str) -> str:
        data = self._artifacts.get(run.run_id, name)
        return "" if data is None else data.decode("utf-8")

    async def _store(self, run: BookRun, name: str, text: str) -> None:
        await asyncio.to_thread(self._artifacts.put, run.run_id, name, text.encode("utf-8"))

    @staticmethod
    def _chapter_name(number: int) -> str:
        return f"chapter_{number:02d}.md"

    @staticmethod
    def _summary_name(number: int) -> str:
        return f"summary_{number:02d}.md"

    @staticmethod
    def _section_name(number: int, section: int) -> str:
        return f"chapter_{number:02d}_s{section:02d}.md"
