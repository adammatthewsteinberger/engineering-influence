"""A novel's recipes and checks, and the two executors that wrap its stages: by kind, and by content level."""

import asyncio
import json
from dataclasses import replace
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.interfaces.stage_output_check_interface import (
    StageOutputCheckInterface,
)
from engineering_influence.interfaces.stage_recipes_interface import StageRecipesInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.content_policy import ContentPolicy
from engineering_influence.services.content_policy_stage_executor import (
    ContentPolicyStageExecutor,
)
from engineering_influence.services.dash_rewriter import DashRewriter
from engineering_influence.services.kind_stage_executor import KindStageExecutor
from engineering_influence.services.local_default_model import LocalDefaultModel
from engineering_influence.services.metadata_parser import MetadataParser
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.novel_output_checks import NovelOutputChecks
from engineering_influence.services.novel_recipes import NovelRecipes
from engineering_influence.services.outline_parser import OutlineParser
from engineering_influence.services.story_bible_parser import StoryBibleParser

BIBLE = json.dumps({"premise": "A heist.", "characters": [{"name": "Ana"}]})
OUTLINE = "## Chapter 1: The Job\nPurpose: Ana plans it.\nBeats:\n- Ana studies the vault\n"


def test_a_novel_runs_from_the_brief_to_a_built_book() -> None:
    plan = NovelRecipes().plan()
    assert plan.kind is BookKind.NOVEL
    assert plan.stages == (
        "brief",
        "story_bible",
        "beats",
        "outline",
        "metadata",
        "draft",
        "assemble",
        "audit",
        "build",
    )


def test_the_draft_is_a_loop_and_has_no_recipe_of_its_own() -> None:
    with pytest.raises(ValueError, match="a novel run has no recipe for stage 'draft'"):
        NovelRecipes().recipe("draft")


def test_it_is_a_set_of_recipes() -> None:
    assert isinstance(NovelRecipes(), StageRecipesInterface)


@pytest.mark.parametrize(
    ("stage", "template", "inputs", "cap"),
    [
        ("brief", "novel_brief", (), 1_500),
        ("story_bible", "novel_story_bible", ("brief",), 4_000),
        ("beats", "novel_beats", ("brief", "story_bible"), 3_000),
        ("outline", "novel_outline", ("brief", "story_bible", "beats"), 5_000),
        ("metadata", "novel_metadata", ("brief", "story_bible", "outline"), 2_500),
    ],
)
def test_each_recipe_names_its_template_inputs_and_cap_and_no_tools(
    stage: str, template: str, inputs: tuple[str, ...], cap: int
) -> None:
    recipe = NovelRecipes().recipe(stage)
    assert (recipe.template, recipe.inputs, recipe.max_output_tokens, recipe.tools) == (
        template,
        inputs,
        cap,
        (),
    )


@pytest.mark.parametrize("stage", ["assemble", "audit", "build"])
def test_the_stages_after_the_draft_have_no_recipe_because_no_model_does_them(stage: str) -> None:
    with pytest.raises(ValueError, match=f"a novel run has no recipe for stage '{stage}'"):
        NovelRecipes().recipe(stage)


def test_a_stage_a_novel_does_not_have_is_refused() -> None:
    with pytest.raises(ValueError, match="a novel run has no recipe for stage 'research'"):
        NovelRecipes().recipe("research")


LISTING = (
    "Title: The Vault\nSubtitle: A heist\nDescription:\n" + "Ana plans one last job. " * 20 + "\n"
    "Keywords:\n- heist\n- thriller\n- vault\n- crew\n- betrayal\n- city\n- night\n"
    "Categories:\n- Books > Literature & Fiction > Thrillers\n"
)
CHECKS = NovelOutputChecks(StoryBibleParser(), OutlineParser(), MetadataParser(DashRewriter()))


def test_it_is_an_output_check() -> None:
    assert isinstance(CHECKS, StageOutputCheckInterface)


def test_a_readable_bible_outline_and_listing_pass() -> None:
    CHECKS.check("story_bible", BIBLE)
    CHECKS.check("outline", OUTLINE)
    CHECKS.check("metadata", LISTING)


def test_an_unreadable_listing_stops_the_run_where_it_was_written() -> None:
    with pytest.raises(ApplicationError) as caught:
        CHECKS.check("metadata", "a blurb with none of the labelled sections")
    assert caught.value.code == "METADATA_INVALID"


def test_an_unreadable_bible_stops_the_run_where_it_was_written() -> None:
    with pytest.raises(ApplicationError) as caught:
        CHECKS.check("story_bible", "no json here")
    assert caught.value.code == "STORY_BIBLE_INVALID"


def test_an_unreadable_outline_stops_the_run_where_it_was_written() -> None:
    with pytest.raises(ApplicationError) as caught:
        CHECKS.check("outline", "no chapters here")
    assert caught.value.code == "OUTLINE_INVALID"


@pytest.mark.parametrize("stage", ["brief", "beats", "anything_else"])
def test_the_other_stages_write_prose_that_nothing_reads(stage: str) -> None:
    CHECKS.check(stage, "free prose that is not JSON and not an outline")


def test_a_bible_is_not_checked_as_an_outline_or_the_reverse() -> None:
    CHECKS.check("beats", BIBLE)
    with pytest.raises(ApplicationError):
        CHECKS.check("story_bible", OUTLINE)
    with pytest.raises(ApplicationError):
        CHECKS.check("outline", BIBLE)


class Recorder(StageExecutorInterface):
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[tuple[str, int]] = []

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        self.calls.append((run.stage, attempt))
        return StageReport()


def run_of(kind: BookKind, stage: str = "brief", **brief: Any) -> BookRun:
    plan = NovelRecipes().plan() if kind is BookKind.NOVEL else NonfictionRecipes().plan()
    return BookRun(
        "r1",
        BookBrief(kind, "an idea", 1_000_000, **brief),
        plan,
        Budget(cap=1_000_000),
        stage=stage,
    )


def test_a_run_goes_to_the_executor_for_its_kind() -> None:
    plain, story = Recorder("plain"), Recorder("story")
    kind = KindStageExecutor({BookKind.NONFICTION: plain, BookKind.NOVEL: story})
    asyncio.run(kind.execute(run_of(BookKind.NOVEL, "beats"), 2))
    asyncio.run(kind.execute(run_of(BookKind.NONFICTION, "brief"), 1))
    assert story.calls == [("beats", 2)]
    assert plain.calls == [("brief", 1)]


def test_the_report_comes_back_from_the_executor() -> None:
    report = asyncio.run(
        KindStageExecutor({BookKind.NOVEL: Recorder("x")}).execute(run_of(BookKind.NOVEL), 1)
    )
    assert isinstance(report, StageReport)


def test_a_kind_with_no_executor_is_refused_by_name() -> None:
    kind = KindStageExecutor({BookKind.NONFICTION: Recorder("plain")})
    with pytest.raises(ApplicationError) as caught:
        asyncio.run(kind.execute(run_of(BookKind.NOVEL), 1))
    assert (caught.value.code, caught.value.http_status) == ("STAGE_KIND_UNSUPPORTED", 422)
    assert caught.value.message == "this build has no stages for a novel book"


MODEL: ProviderDescriptor = LocalDefaultModel({}).descriptor()


def test_a_brief_the_model_allows_goes_through_to_the_stage() -> None:
    inner = Recorder("inner")
    policed = ContentPolicyStageExecutor(inner, ContentPolicy(), MODEL)
    asyncio.run(policed.execute(run_of(BookKind.NOVEL, violence="mild", heat="sweet"), 3))
    asyncio.run(policed.execute(run_of(BookKind.NOVEL), 1))
    assert inner.calls == [("brief", 3), ("brief", 1)]


def test_a_brief_the_model_is_not_recorded_as_allowing_stops_before_the_stage() -> None:
    inner = Recorder("inner")
    policed = ContentPolicyStageExecutor(inner, ContentPolicy(), MODEL)
    with pytest.raises(ApplicationError) as caught:
        asyncio.run(policed.execute(run_of(BookKind.NOVEL, "outline", violence="graphic"), 1))
    assert caught.value.code == "CONTENT_LEVEL_NOT_ALLOWED"
    assert inner.calls == []


def test_a_recorded_ceiling_lets_a_stronger_brief_through() -> None:
    inner = Recorder("inner")
    stronger = replace(MODEL, max_violence="graphic")
    policed = ContentPolicyStageExecutor(inner, ContentPolicy(), stronger)
    asyncio.run(policed.execute(run_of(BookKind.NOVEL, violence="graphic"), 1))
    assert inner.calls == [("brief", 1)]
