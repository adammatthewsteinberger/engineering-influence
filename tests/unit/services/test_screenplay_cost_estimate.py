"""The screenplay draft is priced per scene: about 180 scenes for the three-hour target, one call each."""

from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.services.cost_estimator import CostEstimator
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes

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


def estimate_draft() -> int:
    estimator = CostEstimator(PRICED, {BookKind.SCREENPLAY: ScreenplayRecipes()}, CreateRun.PLANS)
    brief = BookBrief(BookKind.SCREENPLAY, "a bee colony", 5_000_000)
    stages = {name: cost for name, cost, _ in estimator.estimate(brief).stages}
    return stages["draft"]


def test_the_screenplay_draft_is_priced_per_scene() -> None:
    per_scene = CostEstimator.SCENE_INPUT_TOKENS, CostEstimator.SCENE_OUTPUT_TOKENS
    assert estimate_draft() > 0
    assert estimate_draft() == CostEstimator.SCREENPLAY_SCENES * PRICED.cost_micro_usd(
        ModelUsage(*per_scene)
    )


def test_the_screenplay_estimate_covers_every_planned_stage() -> None:
    estimator = CostEstimator(PRICED, {BookKind.SCREENPLAY: ScreenplayRecipes()}, CreateRun.PLANS)
    brief = BookBrief(BookKind.SCREENPLAY, "a bee colony", 5_000_000)
    names = [name for name, _, _ in estimator.estimate(brief).stages]
    assert names == [
        "digest_sources",
        "brief",
        "anchors",
        "audit",
        "beats",
        "scene_cards",
        "visual_grammar",
        "draft",
        "revise_scenes",
        "structure_scenes",
        "dialogue_scenes",
        "assemble_script",
        "lock_script",
        "log_revisions",
        "check_canon",
        "render_script",
        "build_epub",
        "video",
    ]


def test_the_video_stage_is_priced_by_its_shot_list_and_is_optional() -> None:
    estimator = CostEstimator(PRICED, {BookKind.SCREENPLAY: ScreenplayRecipes()}, CreateRun.PLANS)
    brief = BookBrief(BookKind.SCREENPLAY, "a bee colony", 5_000_000)
    stages = {name: (cost, required) for name, cost, required in estimator.estimate(brief).stages}
    assert stages["video"] == (CostEstimator.SCREENPLAY_VIDEO_MICRO_USD, False)
