# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Checks a non-fiction book's factual claims against web pages, and softens the ones no page supports."""

import asyncio
import json
from collections.abc import Callable
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.spend_consent_needed_error import SpendConsentNeededError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.prompt_library_interface import PromptLibraryInterface
from engineering_influence.interfaces.search_provider_interface import SearchProviderInterface
from engineering_influence.interfaces.source_fetcher_interface import SourceFetcherInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.outline import Outline
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.stage_report import StageReport
from engineering_influence.models.tool_loop_result import ToolLoopResult
from engineering_influence.services.interfaces.fact_claim_parser_interface import (
    FactClaimParserInterface,
)
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)
from engineering_influence.services.interfaces.run_tool_loop_interface import (
    RunToolLoopInterface,
)
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface


class FactCheckStageExecutor(StageExecutorInterface):
    """Finds each chapter's checkable claims, searches for them, reads the pages, and keeps only what a page states.

    For each claim the code, not the model, does the searching and the reading. A page is taken as support only when
    the model names it and quotes it, and the quotation is then found word for word in the page the code fetched. A
    quotation the model made up, or a page the model describes without quoting, is not support. The claim is then
    **supported**. A claim that every page the code could read fails to support is **unsupported**; the chapter is
    rewritten by one call that softens or removes exactly those sentences, and kept only if the rewrite is the chapter's
    length to within a tenth and is not a refusal. A claim that could not be searched or read at all is **unchecked**:
    it is reported and left as written, because a failed search is not evidence that a claim is false.

    Every outcome is recorded in ``factrec_NN.json`` for its chapter, and the stage writes ``fact_check.json`` over all of
    them; each finding is a non-blocking issue in the stage report, so it reaches the quality report. The edited
    chapters are ``fact_NN.md``, which is what the book is assembled from. A chapter is done when both of its files
    exist, so a redelivered stage does only the chapters that are not done. Budget runs out the way it does for the
    editing passes: the rest of the chapters are kept as they were and recorded as skipped.
    """

    STAGE: ClassVar[str] = "fact_check"
    OUTPUT: ClassVar[str] = "fact"
    SEARCH_RESULTS: ClassVar[int] = 3
    PAGES_PER_CLAIM: ClassVar[int] = 2
    MAX_PAGE_CHARACTERS: ClassVar[int] = 6_000
    EXTRACT_TOKENS: ClassVar[int] = 2_000
    CHECK_TOKENS: ClassVar[int] = 600
    TOKENS_PER_WORD: ClassVar[float] = 1.6
    OUTPUT_ROOM: ClassVar[int] = 400
    LENGTH_FLOOR: ClassVar[float] = 0.9
    LENGTH_CEILING: ClassVar[float] = 1.1

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        prompts: PromptLibraryInterface,
        outlines: OutlineParserInterface,
        loop: RunToolLoopInterface,
        guards: Callable[[Budget], SpendGuardInterface],
        search: SearchProviderInterface,
        fetcher: SourceFetcherInterface,
        parser: FactClaimParserInterface,
        max_output_tokens: int,
    ) -> None:
        if max_output_tokens < 1:
            raise ValueError("a model has an output limit")
        self._artifacts = artifacts
        self._prompts = prompts
        self._outlines = outlines
        self._loop = loop
        self._guards = guards
        self._search = search
        self._fetcher = fetcher
        self._parser = parser
        self._max_output = max_output_tokens

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Check the chapters that are not done, then write the record over all of them."""
        outline = self._outlines.parse(await self._required(run, "outline.md"))
        guard = self._guards(run.budget)
        skipped_from = await self._skipped(run)
        for chapter in outline.chapters:
            number = chapter.number
            if await self._done(run, number):
                continue
            source = await self._required(run, self._name("copy", number))
            if skipped_from is not None and number >= skipped_from:
                await self._finish(run, number, source, [self._record(number, "skipped")])
                continue
            try:
                text, records = await self._chapter(run, attempt, guard, number, source)
            except SpendConsentNeededError:
                skipped_from = number
                await self._store(run, f"{self.STAGE}_skipped.md", str(number))
                await self._finish(run, number, source, [self._record(number, "skipped")])
                continue
            await self._finish(run, number, text, records)
        records = await self._all_records(run, outline)
        await self._store(
            run, f"{self.STAGE}.json", json.dumps(records, indent=2, ensure_ascii=False) + "\n"
        )
        return StageReport(tuple(self._issues(records)))

    async def _chapter(
        self,
        run: BookRun,
        attempt: int,
        guard: SpendGuardInterface,
        number: int,
        source: str,
    ) -> tuple[str, list[dict[str, str]]]:
        claims = await self._extract(run, attempt, guard, source)
        if claims is None:
            return source, [self._record(number, "unparsed")]
        records: list[dict[str, str]] = []
        for claim, query in claims:
            status, url, quote = await self._verify(run, attempt, guard, claim, query)
            records.append(
                {
                    **self._record(number, status),
                    "claim": claim,
                    "query": query,
                    "url": url,
                    "quote": quote,
                }
            )
        unsupported = [record["claim"] for record in records if record["status"] == "unsupported"]
        if not unsupported:
            return source, records
        edited = await self._soften(run, attempt, guard, source, unsupported)
        for record in records:
            if record["status"] == "unsupported":
                record["status"] = "softened" if edited is not None else "unresolved"
        return (edited if edited is not None else source), records

    async def _extract(
        self, run: BookRun, attempt: int, guard: SpendGuardInterface, source: str
    ) -> tuple[tuple[str, str], ...] | None:
        template = self._prompts.get("stage_extract_claims")
        request = ModelRequest(
            system=template.render("system"),
            prompt=template.render("user", {"chapter": source}),
            max_output_tokens=self.EXTRACT_TOKENS,
            prompt_version=template.identifier(),
        )
        outcome = await self._ask(guard, run, attempt, request)
        if not outcome.complete:
            return None
        return self._parser.claims(outcome.text)

    async def _verify(
        self, run: BookRun, attempt: int, guard: SpendGuardInterface, claim: str, query: str
    ) -> tuple[str, str, str]:
        """The status of one claim, and the page and quotation that support it when it is supported."""
        try:
            hits = await asyncio.to_thread(self._search.search, query, self.SEARCH_RESULTS)
        except (TransientStageError, CapacityExhaustedError):
            return "unchecked", "", ""
        read = False
        for hit in hits[: self.PAGES_PER_CLAIM]:
            try:
                page = await asyncio.to_thread(self._fetcher.fetch, hit.url)
            except (ApplicationError, TransientStageError):
                continue
            read = True
            verdict = await self._judge(
                run, attempt, guard, claim, page.text[: self.MAX_PAGE_CHARACTERS]
            )
            if (
                verdict is not None
                and verdict[0]
                and verdict[1]
                and self._verbatim(verdict[1], page.text)
            ):
                return "supported", hit.url, verdict[1]
        return ("unsupported" if read else "unchecked"), "", ""

    async def _judge(
        self, run: BookRun, attempt: int, guard: SpendGuardInterface, claim: str, page: str
    ) -> tuple[bool, str] | None:
        template = self._prompts.get("stage_check_claim")
        request = ModelRequest(
            system=template.render("system"),
            prompt=template.render("user", {"claim": claim, "page": page}),
            max_output_tokens=self.CHECK_TOKENS,
            prompt_version=template.identifier(),
        )
        outcome = await self._ask(guard, run, attempt, request)
        if not outcome.complete:
            return None
        return self._parser.verdict(outcome.text)

    async def _soften(
        self,
        run: BookRun,
        attempt: int,
        guard: SpendGuardInterface,
        source: str,
        claims: list[str],
    ) -> str | None:
        """The chapter with the unsupported sentences softened or removed, or None when the rewrite is not kept."""
        template = self._prompts.get("stage_soften_claims")
        words = len(source.split())
        output = min(
            int(words * self.TOKENS_PER_WORD * self.LENGTH_CEILING) + self.OUTPUT_ROOM,
            self._max_output,
        )
        listing = "\n".join(f"- {claim}" for claim in claims)
        request = ModelRequest(
            system=template.render("system"),
            prompt=template.render("user", {"claims": listing, "chapter": source}),
            max_output_tokens=output,
            prompt_version=template.identifier(),
        )
        outcome = await self._ask(guard, run, attempt, request)
        if not outcome.complete:
            return None
        text = outcome.text.strip()
        after = len(text.split())
        if not self.LENGTH_FLOOR * words <= after <= self.LENGTH_CEILING * words:
            return None
        return text

    async def _ask(
        self, guard: SpendGuardInterface, run: BookRun, attempt: int, request: ModelRequest
    ) -> ToolLoopResult:
        return await asyncio.to_thread(
            self._loop.run, guard, run.run_id, run.stage, attempt, request
        )

    @staticmethod
    def _verbatim(quote: str, page: str) -> bool:
        """Whether the quotation is in the page word for word, once runs of whitespace are alike."""
        return " ".join(quote.split()) in " ".join(page.split())

    @staticmethod
    def _record(number: int, status: str) -> dict[str, str]:
        return {
            "chapter": str(number),
            "status": status,
            "claim": "",
            "query": "",
            "url": "",
            "quote": "",
        }

    def _issues(self, records: list[dict[str, str]]) -> list[QualityIssue]:
        codes = {
            "softened": "FACT_SOFTENED",
            "unresolved": "FACT_UNRESOLVED",
            "unchecked": "FACT_UNCHECKED",
            "unparsed": "FACT_UNPARSED",
            "skipped": "FACT_SKIPPED",
        }
        issues: list[QualityIssue] = []
        for record in records:
            code = codes.get(record["status"])
            if code is None:
                continue
            what = f": {record['claim']}" if record["claim"] else ""
            issues.append(
                QualityIssue(self.STAGE, code, f"chapter {record['chapter']}{what}", blocking=False)
            )
        return issues

    async def _all_records(self, run: BookRun, outline: Outline) -> list[dict[str, str]]:
        records: list[dict[str, str]] = []
        for chapter in outline.chapters:
            text = await self._required(run, self._record_name(chapter.number))
            records.extend(json.loads(text))
        return records

    async def _done(self, run: BookRun, number: int) -> bool:
        found = await asyncio.to_thread(self._artifacts.names, run.run_id)
        return self._name(self.OUTPUT, number) in found and self._record_name(number) in found

    async def _finish(
        self, run: BookRun, number: int, text: str, records: list[dict[str, str]]
    ) -> None:
        await self._store(run, self._name(self.OUTPUT, number), text)
        await self._store(
            run, self._record_name(number), json.dumps(records, ensure_ascii=False) + "\n"
        )

    async def _skipped(self, run: BookRun) -> int | None:
        marker = await self._read(run, f"{self.STAGE}_skipped.md")
        return None if marker is None else int(marker)

    async def _required(self, run: BookRun, name: str) -> str:
        text = await self._read(run, name)
        if text is None:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {run.stage!r} needs {name}, which this run has not stored",
                http_status=409,
            )
        return text

    @staticmethod
    def _name(prefix: str, number: int) -> str:
        return f"{prefix}_{number:02d}.md"

    @staticmethod
    def _record_name(number: int) -> str:
        return f"factrec_{number:02d}.json"

    async def _read(self, run: BookRun, name: str) -> str | None:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
        return None if data is None else data.decode("utf-8")

    async def _store(self, run: BookRun, name: str, text: str) -> None:
        await asyncio.to_thread(self._artifacts.put, run.run_id, name, text.encode("utf-8"))
