# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FactCheckStageExecutor: a claim is supported only by a page that the code read and a quotation the code found in it."""

import asyncio
import json
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.spend_consent_needed_error import SpendConsentNeededError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.interfaces.search_provider_interface import SearchProviderInterface
from engineering_influence.interfaces.source_fetcher_interface import SourceFetcherInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.fetched_page import FetchedPage
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.search_hit import SearchHit
from engineering_influence.models.stage_report import StageReport
from engineering_influence.models.tool_loop_result import ToolLoopResult
from engineering_influence.services.fact_check_stage_executor import FactCheckStageExecutor
from engineering_influence.services.fact_claim_parser import FactClaimParser
from engineering_influence.services.interfaces.run_tool_loop_interface import (
    RunToolLoopInterface,
)
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.outline_parser import OutlineParser
from engineering_influence.services.spend_guard import SpendGuard

CAP = 5_000_000
OUTLINE = (
    "## Chapter 1: The Hive\nPurpose: How a colony works.\nBeats:\n- The queen\n\n"
    "## Chapter 2: The Site\nPurpose: Where to put it.\nBeats:\n- Sun\n"
)
CHAPTER_ONE = "A colony holds tens of thousands of bees, and the queen lays every egg in it."
CHAPTER_TWO = "Put the hive where the morning sun reaches it, and keep the entrance clear."
PAGE = "Field notes. A colony holds tens of thousands of bees, and the queen lays every egg in it. Ends."
CLAIM = "A colony holds tens of thousands of bees"
HIT = SearchHit("https://example.test/colony", "Colony notes")
EXTRACT_ONE = json.dumps([{"claim": CLAIM, "query": "colony size"}])
SUPPORTED = json.dumps({"supported": True, "quote": CLAIM})
REFUSED = json.dumps({"supported": False, "quote": ""})


def done(text: str) -> ToolLoopResult:
    return ToolLoopResult(text, True, (), 0, 1, 0, 1, ())


def cut(text: str = "partial") -> ToolLoopResult:
    from engineering_influence.models.quality_issue import QualityIssue

    issue = QualityIssue("fact_check", "TRUNCATED", "the answer was cut off", blocking=True)
    return ToolLoopResult(text, False, (issue,), 0, 1, 0, 1, ())


class Loop(RunToolLoopInterface):
    """Answers each kind of prompt from its own queue, and records every request."""

    def __init__(self, answers: dict[str, list[Any]]) -> None:
        self.answers = answers
        self.requests: list[ModelRequest] = []

    def run(
        self,
        guard: Any,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ToolLoopResult:
        self.requests.append(request)
        kind = request.prompt_version.split("@")[0]
        queue = self.answers.get(kind)
        if not queue:
            raise AssertionError(f"unexpected call to {kind}")
        answer = queue.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def calls(self, kind: str) -> int:
        return sum(1 for request in self.requests if request.prompt_version.startswith(kind))


class Search(SearchProviderInterface):
    def __init__(
        self, hits: dict[str, tuple[SearchHit, ...]] | None = None, error: Exception | None = None
    ) -> None:
        self.hits = hits or {}
        self.error = error

    def search(self, query: str, count: int) -> tuple[SearchHit, ...]:
        if self.error is not None:
            raise self.error
        return self.hits.get(query, ())


class Fetcher(SourceFetcherInterface):
    def __init__(self, pages: dict[str, str] | None = None) -> None:
        self.pages = pages or {}

    def fetch(self, url: str) -> FetchedPage:
        if url not in self.pages:
            raise ApplicationError(
                code="SOURCE_UNREACHABLE", message="the page is gone", http_status=502
            )
        return FetchedPage(url, "Page", self.pages[url])


class World:
    def __init__(
        self,
        loop: Loop,
        search: SearchProviderInterface | None = None,
        fetcher: SourceFetcherInterface | None = None,
        copies: tuple[str, str] = (CHAPTER_ONE, CHAPTER_TWO),
        outline: str = OUTLINE,
    ) -> None:
        self.loop = loop
        self.store = InMemoryArtifactStore()
        self.executor = FactCheckStageExecutor(
            self.store,
            TomlPromptLibrary(),
            OutlineParser(),
            loop,
            lambda budget: SpendGuard(budget),
            search or Search(),
            fetcher or Fetcher(),
            FactClaimParser(),
            8_000,
        )
        self.store.put("run-1", "outline.md", outline.encode("utf-8"))
        for number, text in enumerate(copies, start=1):
            self.store.put("run-1", f"copy_{number:02d}.md", text.encode("utf-8"))

    def run(self, attempt: int = 1) -> StageReport:
        brief = BookBrief(BookKind.NONFICTION, "bees", CAP)
        run = BookRun(
            run_id="run-1",
            brief=brief,
            plan=NonfictionRecipes().plan(),
            budget=Budget(cap=CAP, spent=0),
            stage="fact_check",
        )
        return asyncio.run(self.executor.execute(run, attempt))

    def text(self, name: str) -> str | None:
        data = self.store.get("run-1", name)
        return None if data is None else data.decode("utf-8")

    def record(self) -> list[dict[str, str]]:
        return json.loads(self.text("fact_check.json") or "[]")


def codes(report: StageReport) -> list[str]:
    return [issue.code for issue in report.issues]


def supporting_loop(*extra: Any) -> Loop:
    return Loop(
        {
            "stage_extract_claims": [done(EXTRACT_ONE), done("[]")],
            "stage_check_claim": [done(SUPPORTED)],
            **dict(extra),
        }
    )


def test_a_claim_a_read_page_supports_with_a_quotation_it_contains_is_kept_as_written() -> None:
    loop = supporting_loop()
    world = World(loop, search=Search({"colony size": (HIT,)}), fetcher=Fetcher({HIT.url: PAGE}))
    report = world.run()
    assert report.issues == ()
    assert world.text("fact_01.md") == CHAPTER_ONE and world.text("fact_02.md") == CHAPTER_TWO
    (record,) = world.record()
    assert (record["status"], record["url"], record["quote"]) == ("supported", HIT.url, CLAIM)
    assert loop.calls("stage_soften_claims") == 0


def test_a_quotation_matches_the_page_whatever_the_spacing_between_its_words() -> None:
    spaced = json.dumps({"supported": True, "quote": "A colony holds tens of\nthousands of bees"})
    loop = Loop(
        {
            "stage_extract_claims": [done(EXTRACT_ONE), done("[]")],
            "stage_check_claim": [done(spaced)],
        }
    )
    world = World(loop, search=Search({"colony size": (HIT,)}), fetcher=Fetcher({HIT.url: PAGE}))
    world.run()
    assert world.record()[0]["status"] == "supported"


def test_a_second_page_can_support_a_claim_the_first_does_not() -> None:
    second = SearchHit("https://example.test/second", "Second")
    loop = Loop(
        {
            "stage_extract_claims": [done(EXTRACT_ONE), done("[]")],
            "stage_check_claim": [done(REFUSED), done(SUPPORTED)],
        }
    )
    world = World(
        loop,
        search=Search({"colony size": (HIT, second)}),
        fetcher=Fetcher({HIT.url: "Other things.", second.url: PAGE}),
    )
    world.run()
    (record,) = world.record()
    assert (record["status"], record["url"]) == ("supported", second.url)


def test_a_claim_no_page_supports_is_softened_and_listed_as_an_issue() -> None:
    loop = Loop(
        {
            "stage_extract_claims": [done(EXTRACT_ONE), done("[]")],
            "stage_check_claim": [done(REFUSED)],
            "stage_soften_claims": [done(CHAPTER_ONE + " Maybe.")],
        }
    )
    world = World(loop, search=Search({"colony size": (HIT,)}), fetcher=Fetcher({HIT.url: PAGE}))
    report = world.run()
    assert world.text("fact_01.md") == CHAPTER_ONE + " Maybe."
    assert codes(report) == ["FACT_SOFTENED"] and report.issues[0].detail == f"chapter 1: {CLAIM}"
    assert world.record()[0]["status"] == "softened" and not report.issues[0].blocking


def test_a_softening_that_changes_the_length_too_much_is_not_kept_and_the_claim_is_unresolved() -> (
    None
):
    loop = Loop(
        {
            "stage_extract_claims": [done(EXTRACT_ONE), done("[]")],
            "stage_check_claim": [done(REFUSED)],
            "stage_soften_claims": [done("Short.")],
        }
    )
    world = World(loop, search=Search({"colony size": (HIT,)}), fetcher=Fetcher({HIT.url: PAGE}))
    report = world.run()
    assert world.text("fact_01.md") == CHAPTER_ONE
    assert codes(report) == ["FACT_UNRESOLVED"] and world.record()[0]["status"] == "unresolved"


def test_a_softening_that_is_cut_off_is_not_kept() -> None:
    loop = Loop(
        {
            "stage_extract_claims": [done(EXTRACT_ONE), done("[]")],
            "stage_check_claim": [done(REFUSED)],
            "stage_soften_claims": [cut(CHAPTER_ONE)],
        }
    )
    world = World(loop, search=Search({"colony size": (HIT,)}), fetcher=Fetcher({HIT.url: PAGE}))
    assert codes(world.run()) == ["FACT_UNRESOLVED"]
    assert world.text("fact_01.md") == CHAPTER_ONE


def test_a_quotation_that_is_not_in_the_page_is_not_support_however_confident_the_model_is() -> (
    None
):
    invented = json.dumps({"supported": True, "quote": "Bees hold a parliament every spring."})
    loop = Loop(
        {
            "stage_extract_claims": [done(EXTRACT_ONE), done("[]")],
            "stage_check_claim": [done(invented)],
            "stage_soften_claims": [done(CHAPTER_ONE)],
        }
    )
    world = World(loop, search=Search({"colony size": (HIT,)}), fetcher=Fetcher({HIT.url: PAGE}))
    report = world.run()
    assert world.record()[0]["status"] == "softened" and codes(report) == ["FACT_SOFTENED"]


def test_a_check_that_cannot_be_read_is_not_support() -> None:
    loop = Loop(
        {
            "stage_extract_claims": [done(EXTRACT_ONE), done("[]")],
            "stage_check_claim": [cut("supported")],
            "stage_soften_claims": [done(CHAPTER_ONE)],
        }
    )
    world = World(loop, search=Search({"colony size": (HIT,)}), fetcher=Fetcher({HIT.url: PAGE}))
    world.run()
    assert world.record()[0]["status"] == "softened"


def test_a_claim_that_cannot_be_searched_is_unchecked_and_left_as_written() -> None:
    loop = Loop({"stage_extract_claims": [done(EXTRACT_ONE), done("[]")]})
    world = World(loop)
    report = world.run()
    assert codes(report) == ["FACT_UNCHECKED"] and report.issues[0].detail == f"chapter 1: {CLAIM}"
    assert world.record()[0]["status"] == "unchecked"
    assert loop.calls("stage_check_claim") == 0 and loop.calls("stage_soften_claims") == 0


def test_a_search_that_fails_for_now_leaves_the_claim_unchecked() -> None:
    loop = Loop({"stage_extract_claims": [done(EXTRACT_ONE), done("[]")]})
    world = World(loop, search=Search(error=TransientStageError("the search timed out")))
    assert codes(world.run()) == ["FACT_UNCHECKED"]


def test_pages_that_cannot_be_read_leave_the_claim_unchecked() -> None:
    loop = Loop({"stage_extract_claims": [done(EXTRACT_ONE), done("[]")]})
    world = World(loop, search=Search({"colony size": (HIT,)}), fetcher=Fetcher({}))
    assert codes(world.run()) == ["FACT_UNCHECKED"]
    assert loop.calls("stage_check_claim") == 0


def test_an_unreadable_claim_list_leaves_the_chapter_as_it_was_and_is_reported() -> None:
    loop = Loop({"stage_extract_claims": [done("I cannot list them."), done("[]")]})
    report = World(loop).run()
    assert codes(report) == ["FACT_UNPARSED"] and report.issues[0].detail == "chapter 1"


def test_a_claim_list_cut_off_is_unreadable() -> None:
    loop = Loop({"stage_extract_claims": [cut("[{"), done("[]")]})
    assert codes(World(loop).run()) == ["FACT_UNPARSED"]


def test_a_chapter_with_no_claims_makes_no_further_calls() -> None:
    loop = Loop({"stage_extract_claims": [done("[]"), done("[]")]})
    world = World(loop)
    report = world.run()
    assert report.issues == () and loop.calls("stage_check_claim") == 0
    assert world.record() == []


def test_running_out_of_money_keeps_the_rest_of_the_book_as_written_and_says_so() -> None:
    loop = Loop({"stage_extract_claims": [SpendConsentNeededError(250_000)]})
    world = World(loop)
    report = world.run()
    assert codes(report) == ["FACT_SKIPPED", "FACT_SKIPPED"]
    assert world.text("fact_check_skipped.md") == "1"
    assert world.text("fact_01.md") == CHAPTER_ONE and world.text("fact_02.md") == CHAPTER_TWO
    assert len(loop.requests) == 1


def test_a_redelivered_stage_does_only_the_chapters_that_are_not_done() -> None:
    loop = supporting_loop()
    world = World(loop, search=Search({"colony size": (HIT,)}), fetcher=Fetcher({HIT.url: PAGE}))
    first = world.run()
    calls = len(loop.requests)
    second = world.run(attempt=2)
    assert len(loop.requests) == calls
    assert first.issues == second.issues == ()


def test_a_chapter_with_no_copy_edit_is_a_missing_input() -> None:
    outline = OUTLINE + "\n## Chapter 3: Missing\nPurpose: None.\nBeats:\n- None\n"
    world = World(
        Loop({"stage_extract_claims": [done("[]"), done("[]"), done("[]")]}), outline=outline
    )
    with pytest.raises(ApplicationError) as error:
        world.run()
    assert error.value.code == "STAGE_INPUT_MISSING"


def test_a_model_with_no_room_for_an_answer_is_refused_before_the_stage_starts() -> None:
    with pytest.raises(ValueError, match="output limit"):
        FactCheckStageExecutor(
            InMemoryArtifactStore(),
            TomlPromptLibrary(),
            OutlineParser(),
            Loop({}),
            lambda budget: SpendGuard(budget),
            Search(),
            Fetcher(),
            FactClaimParser(),
            0,
        )


def test_the_stage_is_named_for_its_output() -> None:
    assert FactCheckStageExecutor.STAGE == "fact_check" and FactCheckStageExecutor.OUTPUT == "fact"


def test_a_chapter_with_a_supported_and_an_unsupported_claim_softens_only_the_unsupported_one() -> (
    None
):
    both = json.dumps(
        [
            {"claim": CLAIM, "query": "colony size"},
            {"claim": "Bees fly to Mars", "query": "bee mars"},
        ]
    )
    loop = Loop(
        {
            "stage_extract_claims": [done(both), done("[]")],
            "stage_check_claim": [done(SUPPORTED), done(REFUSED)],
            "stage_soften_claims": [done(CHAPTER_ONE)],
        }
    )
    world = World(
        loop,
        search=Search({"colony size": (HIT,), "bee mars": (HIT,)}),
        fetcher=Fetcher({HIT.url: PAGE}),
    )
    report = world.run()
    assert [record["status"] for record in world.record()] == ["supported", "softened"]
    assert (
        codes(report) == ["FACT_SOFTENED"]
        and report.issues[0].detail == "chapter 1: Bees fly to Mars"
    )
