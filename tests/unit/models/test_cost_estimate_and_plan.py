"""CostEstimate, BudgetPlan and SpendSummary: the arithmetic of what a book is expected to cost."""

import pytest

from engineering_influence.models.budget_plan import BudgetPlan
from engineering_influence.models.cost_estimate import CostEstimate
from engineering_influence.models.interfaces.budget_plan_interface import BudgetPlanInterface
from engineering_influence.models.interfaces.cost_estimate_interface import CostEstimateInterface
from engineering_influence.models.interfaces.spend_summary_interface import SpendSummaryInterface
from engineering_influence.models.spend_summary import SpendSummary

ESTIMATE = CostEstimate(
    (
        ("brief", 1_000_000, True),
        ("draft", 3_000_000, True),
        ("copy_edit", 2_000_000, False),
        ("build", 0, True),
    )
)


def test_an_estimate_adds_up_what_is_essential_and_what_is_optional() -> None:
    assert isinstance(ESTIMATE, CostEstimateInterface)
    assert (ESTIMATE.expected(), ESTIMATE.essential(), ESTIMATE.optional()) == (
        6_000_000,
        4_000_000,
        2_000_000,
    )


def test_the_margin_is_half_again_rounded_up() -> None:
    assert ESTIMATE.high(4_000_000) == 6_000_000
    assert ESTIMATE.high(3) == 5 and ESTIMATE.high(0) == 0 and ESTIMATE.high(1) == 2


@pytest.mark.parametrize(
    "stages",
    [
        (),
        (("a", 1, True), ("a", 2, False)),
        (("a", -1, True),),
        (("a", 1.5, True),),
    ],
)
def test_an_estimate_needs_stages_named_once_with_whole_non_negative_costs(
    stages: tuple[object, ...],
) -> None:
    with pytest.raises(ValueError):
        CostEstimate(stages)  # type: ignore[arg-type]


def test_a_stage_list_that_is_not_a_tuple_is_refused() -> None:
    with pytest.raises(ValueError, match="at least one stage"):
        CostEstimate([("a", 1, True)])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("cap", "grade"),
    [
        (3_999_999, "short"),
        (4_000_000, "tight"),
        (5_999_999, "tight"),
        (6_000_000, "lean"),
        (8_999_999, "lean"),
        (9_000_000, "ample"),
    ],
)
def test_a_cap_is_graded_against_the_estimate_at_each_boundary(cap: int, grade: str) -> None:
    plan = BudgetPlan(cap, ESTIMATE)
    assert isinstance(plan, BudgetPlanInterface)
    assert plan.grade() == grade
    assert plan.suggested() == 9_000_000


@pytest.mark.parametrize("bad", [0, -1, 1.5, True])
def test_a_plan_needs_a_cap_above_zero(bad: object) -> None:
    with pytest.raises(ValueError, match="whole number of micro-dollars above zero"):
        BudgetPlan(bad, ESTIMATE)  # type: ignore[arg-type]


def test_a_spend_summary_says_how_far_the_spend_was_from_the_estimate() -> None:
    summary = SpendSummary(5_000_000, 1_500_000, 1_000_000, 1_500_000)
    assert isinstance(summary, SpendSummaryInterface)
    assert summary.ratio() == 1.5
    assert SpendSummary(10, 1, 3).ratio() == 0.333


def test_with_no_estimate_there_is_no_ratio_and_a_zero_estimate_is_no_estimate() -> None:
    assert SpendSummary(10, 5).ratio() is None
    assert SpendSummary(10, 5, 0, 0).ratio() is None


@pytest.mark.parametrize("field", ["cap", "spent", "estimated", "estimated_high"])
@pytest.mark.parametrize("bad", [-1, 1.5, True])
def test_a_spend_summary_holds_whole_non_negative_amounts(field: str, bad: object) -> None:
    fields: dict[str, object] = {"cap": 10, "spent": 1, "estimated": 2, "estimated_high": 3}
    fields[field] = bad
    with pytest.raises(ValueError, match=f"{field} is a whole number"):
        SpendSummary(**fields)  # type: ignore[arg-type]
