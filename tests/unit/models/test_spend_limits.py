"""SpendLimits: the operator's two ceilings, read from the environment, each optional."""

from typing import Any

import pytest

from engineering_influence.models.interfaces.spend_limits_interface import SpendLimitsInterface
from engineering_influence.models.spend_limits import SpendLimits


def test_no_ceiling_is_set_by_default() -> None:
    limits = SpendLimits()
    assert isinstance(limits, SpendLimitsInterface)
    assert (limits.per_run, limits.outstanding) == (None, None)


@pytest.mark.parametrize("bad", [0, -1, 1.5, True, "5"])
@pytest.mark.parametrize("field", ["per_run", "outstanding"])
def test_a_ceiling_is_a_whole_number_of_micro_dollars_above_zero(field: str, bad: Any) -> None:
    with pytest.raises(ValueError, match=f"{field} is a whole number"):
        SpendLimits(**{field: bad})


def test_one_run_cannot_be_allowed_more_than_all_runs_together() -> None:
    SpendLimits(per_run=5, outstanding=5)
    with pytest.raises(ValueError, match="one run may not be allowed more than all runs"):
        SpendLimits(per_run=6, outstanding=5)


def test_the_environment_sets_each_ceiling_and_blank_or_absent_sets_none() -> None:
    assert SpendLimits.from_environment({}) == SpendLimits()
    assert SpendLimits.from_environment(
        {
            "EI_MAX_RUN_BUDGET_MICRO_USD": " 3000000 ",
            "EI_MAX_OUTSTANDING_BUDGET_MICRO_USD": "10000000",
        }
    ) == SpendLimits(3_000_000, 10_000_000)
    assert SpendLimits.from_environment({"EI_MAX_RUN_BUDGET_MICRO_USD": "  "}) == SpendLimits()
    assert SpendLimits.from_environment(
        {"EI_MAX_OUTSTANDING_BUDGET_MICRO_USD": "7"}
    ) == SpendLimits(None, 7)


@pytest.mark.parametrize("bad", ["0", "-5", "five", "2.5", "1e6"])
@pytest.mark.parametrize(
    "name", ["EI_MAX_RUN_BUDGET_MICRO_USD", "EI_MAX_OUTSTANDING_BUDGET_MICRO_USD"]
)
def test_a_ceiling_that_is_not_a_whole_number_is_refused_by_name(name: str, bad: str) -> None:
    with pytest.raises(ValueError, match=f"{name} must be a whole number"):
        SpendLimits.from_environment({name: bad})


def test_ceilings_that_contradict_each_other_are_refused_with_both_names() -> None:
    with pytest.raises(ValueError, match="EI_MAX_RUN_BUDGET_MICRO_USD and EI_MAX_OUTSTANDING"):
        SpendLimits.from_environment(
            {"EI_MAX_RUN_BUDGET_MICRO_USD": "9", "EI_MAX_OUTSTANDING_BUDGET_MICRO_USD": "5"}
        )
