"""The pure models a run is built from: the brief, the plan, the run, sources and the bible."""

import pytest

from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.source_record import SourceRecord
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.story_bible import StoryBible
from engineering_influence.models.story_character import StoryCharacter

STAGES = ("brief", "outline", "draft", "package")


def brief(kind: BookKind = BookKind.NONFICTION, **changes: object) -> BookBrief:
    fields: dict[str, object] = {
        "kind": kind,
        "idea": "a field guide to sourdough",
        "budget_micro_usd": 5_000_000,
    }
    fields.update(changes)
    return BookBrief(**fields)  # type: ignore[arg-type]


def plan(kind: BookKind = BookKind.NONFICTION) -> StagePlan:
    return StagePlan(kind=kind, stages=STAGES)


def run(**changes: object) -> BookRun:
    fields: dict[str, object] = {
        "run_id": "run-1",
        "brief": brief(),
        "plan": plan(),
        "budget": Budget(cap=5_000_000),
    }
    fields.update(changes)
    return BookRun(**fields)  # type: ignore[arg-type]


def test_a_brief_needs_only_a_kind_an_idea_and_a_budget() -> None:
    value = brief()
    assert (value.title_hint, value.audience, value.target_words, value.trim_size) == (None,) * 4
    assert value.language == "en"


def test_a_brief_keeps_what_it_is_given() -> None:
    value = brief(
        BookKind.NOVEL,
        title_hint="Rise",
        audience="home bakers",
        target_words=60_000,
        trim_size="5.5x8.5",
        language="fr",
    )
    assert (value.kind, value.title_hint, value.target_words, value.language) == (
        BookKind.NOVEL,
        "Rise",
        60_000,
        "fr",
    )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"idea": "  "}, "needs an idea"),
        ({"budget_micro_usd": 0}, "positive budget"),
        ({"budget_micro_usd": -1}, "positive budget"),
        ({"target_words": 0}, "target words"),
        ({"language": " "}, "needs a language"),
        ({"title_hint": ""}, "cannot be blank"),
        ({"audience": " "}, "cannot be blank"),
        ({"trim_size": ""}, "trim size must be one of"),
        ({"trim_size": "7x10"}, "5x8, 5.5x8.5, 6x9"),
    ],
)
def test_a_brief_refuses_what_cannot_start_a_run(changes: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        brief(**changes)


@pytest.mark.parametrize("stages", [(), ("a", " ")])
def test_a_plan_needs_named_stages(stages: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="at least one named stage"):
        StagePlan(kind=BookKind.NOVEL, stages=stages)


def test_a_plan_refuses_a_repeated_stage() -> None:
    with pytest.raises(ValueError, match="distinct"):
        StagePlan(kind=BookKind.NOVEL, stages=("a", "b", "a"))


def test_a_plan_walks_its_stages_in_order() -> None:
    value = plan()
    assert value.first() == "brief"
    assert [value.after(stage) for stage in STAGES] == ["outline", "draft", "package", None]


def test_a_plan_has_no_stage_after_one_it_does_not_contain() -> None:
    with pytest.raises(ValueError, match="'nope' is not a stage"):
        plan().after("nope")


@pytest.mark.parametrize(("url", "digest"), [("", "abc"), ("https://x", " ")])
def test_a_source_needs_a_url_and_a_hash(url: str, digest: str) -> None:
    with pytest.raises(ValueError, match="url and a content hash"):
        SourceRecord(url=url, title="t", content_hash=digest)


def test_verifying_a_source_returns_a_new_one() -> None:
    source = SourceRecord(url="https://example.org/a", title="A", content_hash="abc")
    checked = source.mark_verified()
    assert (source.verified, checked.verified) == (False, True)
    assert (checked.url, checked.content_hash) == (source.url, source.content_hash)


def test_a_story_bible_needs_a_premise() -> None:
    with pytest.raises(ValueError, match="the premise needs text"):
        StoryBible(premise=" ")


def test_a_story_bible_refuses_two_characters_with_one_name() -> None:
    with pytest.raises(ValueError, match="character names must be distinct"):
        StoryBible(premise="a heist", characters=(StoryCharacter("Ana"), StoryCharacter("Ana")))


def test_a_story_bible_defaults_to_nothing_but_the_premise() -> None:
    bible = StoryBible(premise="a heist")
    assert (bible.characters, bible.places, bible.timeline) == ((), (), ())


def test_a_new_run_starts_pending_on_the_first_stage() -> None:
    value = run()
    assert (value.status, value.stage, value.issues) == (RunStatus.PENDING, "brief", ())


def test_a_run_may_start_on_a_later_stage() -> None:
    assert run(stage="draft").stage == "draft"


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"run_id": " "}, "needs an id"),
        ({"plan": plan(BookKind.NOVEL)}, "different kind of book"),
        ({"stage": "typeset"}, "'typeset' is not a stage"),
    ],
)
def test_a_run_refuses_a_plan_or_stage_that_does_not_fit(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        run(**changes)


def test_advancing_walks_the_plan_and_then_completes() -> None:
    value = run()
    seen = [value.stage]
    while value.status is not RunStatus.COMPLETED:
        value = value.advance()
        seen.append(value.stage)
    assert seen == ["brief", "outline", "draft", "package", "package"]
    assert value.status is RunStatus.COMPLETED


def test_advancing_leaves_the_original_run_alone() -> None:
    first = run()
    first.advance()
    assert (first.stage, first.status) == ("brief", RunStatus.PENDING)


def test_a_run_parks_and_resumes_on_the_same_stage() -> None:
    parked = run(stage="draft").park()
    assert (parked.status, parked.stage) == (RunStatus.PARKED_CAPACITY, "draft")
    resumed = parked.resume()
    assert (resumed.status, resumed.stage) == (RunStatus.RUNNING, "draft")


@pytest.mark.parametrize("status", [RunStatus.PENDING, RunStatus.RUNNING, RunStatus.COMPLETED])
def test_only_a_parked_run_can_resume(status: RunStatus) -> None:
    with pytest.raises(ValueError, match="only a parked run can resume"):
        run(status=status).resume()


@pytest.mark.parametrize(
    ("end", "expected"),
    [(BookRun.fail, RunStatus.FAILED), (BookRun.cancel, RunStatus.CANCELLED)],
)
def test_a_run_can_be_ended_early(end: object, expected: RunStatus) -> None:
    assert end(run()).status is expected  # type: ignore[operator]


@pytest.mark.parametrize("status", [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED])
@pytest.mark.parametrize("move", [BookRun.advance, BookRun.park, BookRun.fail, BookRun.cancel])
def test_a_finished_run_cannot_move(status: RunStatus, move: object) -> None:
    with pytest.raises(ValueError, match="already finished"):
        move(run(status=status))  # type: ignore[operator]


def test_a_run_swaps_in_a_new_budget() -> None:
    value = run()
    reserved = value.budget.reserve(1_000_000)
    assert value.with_budget(reserved).budget.remaining() == 4_000_000
    assert value.budget.remaining() == 5_000_000


def test_a_run_collects_issues_and_knows_whether_one_blocks() -> None:
    value = run()
    assert value.has_blocking_issue() is False
    minor = QualityIssue(stage="draft", code="thin", detail="400 words")
    blocker = QualityIssue(stage="package", code="epubcheck", detail="3 errors", blocking=True)
    noted = value.with_issue(minor)
    assert (noted.issues, noted.has_blocking_issue()) == ((minor,), False)
    blocked = noted.with_issue(blocker)
    assert (blocked.issues, blocked.has_blocking_issue()) == ((minor, blocker), True)


def test_a_pending_run_starts() -> None:
    started = run().start()
    assert (started.status, started.stage) == (RunStatus.RUNNING, "brief")


@pytest.mark.parametrize(
    "status", [RunStatus.RUNNING, RunStatus.PARKED_CAPACITY, RunStatus.COMPLETED, RunStatus.FAILED]
)
def test_only_a_pending_run_can_start(status: RunStatus) -> None:
    with pytest.raises(ValueError, match="only a pending run can start"):
        run(status=status).start()
