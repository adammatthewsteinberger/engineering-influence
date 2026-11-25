"""The estimator's arithmetic: chapters from words, tokens from chapters, prices from the model's own rates."""

from dataclasses import replace

from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.services.budget_planner import BudgetPlanner
from engineering_influence.services.cost_estimator import CostEstimator
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.interfaces.budget_planner_interface import (
    BudgetPlannerInterface,
)
from engineering_influence.services.interfaces.cost_estimator_interface import (
    CostEstimatorInterface,
)
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.novel_recipes import NovelRecipes

PRICED = ProviderDescriptor(
    provider="fake",
    model="fake-1",
    family="fake",
    context_window=200_000,
    max_output_tokens=8_000,
    input_micro_usd_per_mtok=1_000_000,
    output_micro_usd_per_mtok=5_000_000,
    cache_read_micro_usd_per_mtok=0,
    cache_write_micro_usd_per_mtok=0,
    batch_discount_percent=0,
    price_effective="2026-11-01",
    usage_policy_url="https://example.test/policy",
)
FREE = ProviderDescriptor(
    provider="local",
    model="m",
    family="m",
    context_window=200_000,
    max_output_tokens=8_000,
    input_micro_usd_per_mtok=0,
    output_micro_usd_per_mtok=0,
    cache_read_micro_usd_per_mtok=0,
    cache_write_micro_usd_per_mtok=0,
    batch_discount_percent=0,
    price_effective="2026-11-01",
    usage_policy_url="https://example.test/policy",
)
RECIPES = {BookKind.NONFICTION: NonfictionRecipes(), BookKind.NOVEL: NovelRecipes()}


def estimator(descriptor: ProviderDescriptor = PRICED) -> CostEstimator:
    return CostEstimator(descriptor, RECIPES, CreateRun.PLANS)


def brief(kind: BookKind = BookKind.NONFICTION, words: int | None = 20_000) -> BookBrief:
    return BookBrief(kind, "bees", 5_000_000, target_words=words)


def by_stage(
    book: BookBrief, descriptor: ProviderDescriptor = PRICED
) -> dict[str, tuple[int, bool]]:
    return {
        name: (cost, essential)
        for name, cost, essential in estimator(descriptor).estimate(book).stages
    }


def cost(input_tokens: int, output_tokens: int) -> int:
    return PRICED.cost_micro_usd(ModelUsage(input_tokens, output_tokens))


def test_it_is_a_cost_estimator() -> None:
    assert isinstance(estimator(), CostEstimatorInterface)


def test_every_stage_of_the_plan_is_estimated_in_order() -> None:
    estimate = estimator().estimate(brief())
    assert [name for name, _, _ in estimate.stages] == list(NonfictionRecipes().plan().stages)
    novel = estimator().estimate(brief(BookKind.NOVEL))
    assert [name for name, _, _ in novel.stages] == list(NovelRecipes().plan().stages)


def test_the_stages_that_call_no_model_cost_nothing() -> None:
    stages = by_stage(brief())
    assert [stages[name] for name in ("assemble", "audit", "build")] == [(0, True)] * 3


def test_the_editing_passes_are_optional_and_everything_else_is_essential() -> None:
    stages = by_stage(brief())
    assert {name for name, (_, essential) in stages.items() if not essential} == {
        "revise_structure",
        "revise_lines",
        "copy_edit",
        "fact_check",
    }
    assert {
        name for name, (_, essential) in by_stage(brief(BookKind.NOVEL)).items() if not essential
    } == {
        "revise_story",
        "revise_lines",
        "copy_edit",
    }


def test_a_planning_stage_is_priced_from_its_recipe_with_a_share_of_the_output_cap() -> None:
    stages = by_stage(brief())
    outline = NonfictionRecipes().recipe("outline")
    expected = cost(
        CostEstimator.PLANNING_INPUT_TOKENS,
        outline.max_output_tokens * CostEstimator.PLANNING_OUTPUT_PERCENT // 100,
    )
    assert stages["outline"][0] == expected


def test_a_stage_with_tools_makes_several_calls() -> None:
    research = NonfictionRecipes().recipe("research")
    single = cost(
        CostEstimator.PLANNING_INPUT_TOKENS,
        research.max_output_tokens * CostEstimator.PLANNING_OUTPUT_PERCENT // 100,
    )
    assert research.tools and by_stage(brief())["research"][0] == single * CostEstimator.TOOL_TURNS


def test_a_book_is_twenty_thousand_words_unless_the_brief_says_otherwise() -> None:
    assert estimator().estimate(brief(words=None)) == estimator().estimate(brief(words=20_000))
    assert (
        estimator().estimate(brief(words=60_000)).expected()
        > estimator().estimate(brief(words=20_000)).expected()
    )


def test_the_number_of_chapters_is_held_between_three_and_thirty() -> None:
    few = by_stage(brief(words=100))["copy_edit"][0]
    many = by_stage(brief(words=10_000_000))["copy_edit"][0]
    chapter_tokens_few = round(100 / 3 * CostEstimator.TOKENS_PER_WORD)
    assert few == 3 * cost(
        chapter_tokens_few + CostEstimator.EDIT_INSTRUCTION_TOKENS, chapter_tokens_few
    )
    chapter_tokens_many = round(10_000_000 / 30 * CostEstimator.TOKENS_PER_WORD)
    assert many == 30 * cost(
        chapter_tokens_many + CostEstimator.EDIT_INSTRUCTION_TOKENS, chapter_tokens_many
    )


def test_the_draft_reads_a_context_that_grows_and_writes_the_chapter_and_a_summary() -> None:
    chapters = round(20_000 / CostEstimator.WORDS_PER_CHAPTER)
    chapter_tokens = round(20_000 / chapters * CostEstimator.TOKENS_PER_WORD)
    expected = sum(
        cost(
            CostEstimator.CONTEXT_BASE_TOKENS + CostEstimator.CONTEXT_PER_CHAPTER_TOKENS * n,
            chapter_tokens,
        )
        + cost(chapter_tokens, CostEstimator.SUMMARY_OUTPUT_TOKENS)
        for n in range(chapters)
    )
    assert by_stage(brief())["draft"][0] == expected


def test_a_free_model_costs_nothing_and_a_dearer_one_costs_more() -> None:
    assert estimator(FREE).estimate(brief()).expected() == 0
    dearer = replace(
        PRICED, input_micro_usd_per_mtok=3_000_000, output_micro_usd_per_mtok=15_000_000
    )
    cheap = estimator().estimate(brief()).expected()
    assert abs(estimator(dearer).estimate(brief()).expected() - 3 * cheap) < 200


def test_a_stage_with_no_recipe_gets_a_default_planning_cost() -> None:
    bare = CostEstimator(PRICED, {}, CreateRun.PLANS)
    assert {n: c for n, c, _ in bare.estimate(brief()).stages}["outline"] == cost(
        CostEstimator.PLANNING_INPUT_TOKENS, CostEstimator.DEFAULT_PLANNING_OUTPUT
    )


def test_the_planner_grades_a_brief_against_the_estimate() -> None:
    planner = BudgetPlanner(estimator())
    assert isinstance(planner, BudgetPlannerInterface)
    plan = planner.plan(brief())
    assert plan.cap == 5_000_000 and plan.estimate == estimator().estimate(brief())
    tiny = BookBrief(BookKind.NONFICTION, "bees", 1, target_words=20_000)
    assert planner.plan(tiny).grade() == "short"
    free = BudgetPlanner(estimator(FREE)).plan(tiny)
    assert free.grade() == "ample"
