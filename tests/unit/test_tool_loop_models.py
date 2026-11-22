# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The models of the tool loop: limits, result, schema check, the allowlist and tool turns."""

import math
from typing import Any

import pytest

from engineering_influence.models.model_answer import ModelAnswer
from engineering_influence.models.model_call_result import ModelCallResult
from engineering_influence.models.model_turn import ModelTurn
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.stage_recipe import StageRecipe
from engineering_influence.models.tool_call import ToolCall
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_loop_limits import ToolLoopLimits
from engineering_influence.models.tool_loop_result import ToolLoopResult
from engineering_influence.models.tool_result import ToolResult

CALL = ToolCall("c1", "web_search", {"query": "bees"})
ISSUE = QualityIssue("research", "TRUNCATED", "ran out of room", blocking=True)
TURN = ModelTurn("t", (CALL,), (ToolResult("c1", "r"),))


# ------------------------------------------------------------------------- ToolLoopLimits
def test_the_limits_have_sensible_defaults() -> None:
    limits = ToolLoopLimits()
    assert (limits.max_turns, limits.max_tool_calls) == (8, 16)
    assert (limits.result_characters, limits.call_seconds) == (20_000, 60.0)


@pytest.mark.parametrize("name", ["max_turns", "max_tool_calls", "result_characters"])
@pytest.mark.parametrize("value", [0, -1, True, 1.5, "3"])
def test_a_count_limit_is_a_whole_number_from_one(name: str, value: Any) -> None:
    with pytest.raises(ValueError, match=f"{name} is a whole number from 1"):
        ToolLoopLimits(**{name: value})


def test_the_smallest_count_limits_are_allowed() -> None:
    limits = ToolLoopLimits(max_turns=1, max_tool_calls=1, result_characters=1, call_seconds=0.001)
    assert limits.max_turns == 1


@pytest.mark.parametrize("value", [0, -1.0, True, math.nan])
def test_the_call_time_is_more_than_zero(value: Any) -> None:
    with pytest.raises(ValueError, match="call_seconds is more than zero"):
        ToolLoopLimits(call_seconds=value)


def test_room_for_counts_calls_up_to_and_including_the_cap() -> None:
    limits = ToolLoopLimits(max_tool_calls=4)
    assert limits.room_for(0, 4)
    assert limits.room_for(3, 1)
    assert not limits.room_for(4, 1)
    assert not limits.room_for(3, 2)
    assert not limits.room_for(0, 5)


# ------------------------------------------------------------------------- ToolLoopResult
def result(**changes: Any) -> ToolLoopResult:
    fields: dict[str, Any] = {
        "text": "done",
        "complete": True,
        "issues": (),
        "cost_micro_usd": 5,
        "model_calls": 1,
        "tool_calls": 0,
        "turns": 1,
        "transcript": (),
    }
    return ToolLoopResult(**{**fields, **changes})


def test_a_finished_loop_has_no_issues_and_an_unfinished_one_says_why() -> None:
    assert result().complete
    assert not result(complete=False, issues=(ISSUE,)).complete
    with pytest.raises(ValueError, match="a finished loop has no issues"):
        result(issues=(ISSUE,))
    with pytest.raises(ValueError, match="must say what went wrong"):
        result(complete=False)


@pytest.mark.parametrize("name", ["cost_micro_usd", "model_calls", "tool_calls", "turns"])
def test_a_result_has_no_negative_numbers(name: str) -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        result(**{name: -1})
    assert result(**{name: 0}).complete


def test_a_loop_used_tools_when_it_has_a_transcript() -> None:
    assert not result().used_tools()
    assert result(transcript=(TURN,), tool_calls=1).used_tools()


# ------------------------------------------------------------------ ToolDefinition.check
def definition(**schema: Any) -> ToolDefinition:
    return ToolDefinition("t", "A tool.", {"type": "object", **schema})


def test_arguments_that_fit_pass() -> None:
    tool = definition(
        properties={"q": {"type": "string"}, "n": {"type": "integer"}}, required=["q"]
    )
    assert tool.check({"q": "x"}) == ""
    assert tool.check({"q": "x", "n": 3}) == ""
    assert definition().check({}) == ""
    assert definition().check({"anything": [1]}) == ""


def test_a_missing_required_argument_is_named() -> None:
    tool = definition(properties={"q": {"type": "string"}}, required=["q"])
    assert tool.check({}) == "missing the required argument 'q'"


@pytest.mark.parametrize(
    ("kind", "good", "bad"),
    [
        ("string", "x", 5),
        ("integer", 3, 3.5),
        ("integer", 3, True),
        ("integer", 3, "3"),
        ("number", 3.5, "3.5"),
        ("number", 3, True),
        ("boolean", True, 1),
        ("array", [1], {"a": 1}),
        ("object", {"a": 1}, [1]),
    ],
)
def test_each_type_is_checked(kind: str, good: Any, bad: Any) -> None:
    tool = definition(properties={"v": {"type": kind}})
    assert tool.check({"v": good}) == ""
    assert tool.check({"v": bad}) == f"argument 'v' must be of type {kind}"


def test_a_number_may_be_a_whole_number_or_a_fraction() -> None:
    tool = definition(properties={"v": {"type": "number"}})
    assert tool.check({"v": 2}) == tool.check({"v": 2.5}) == ""


def test_an_enum_limits_the_values() -> None:
    tool = definition(properties={"mode": {"type": "string", "enum": ["fast", "slow"]}})
    assert tool.check({"mode": "fast"}) == ""
    assert tool.check({"mode": "medium"}) == "argument 'mode' must be one of ['fast', 'slow']"


def test_an_extra_argument_is_allowed_unless_the_schema_forbids_it() -> None:
    open_tool = definition(properties={"q": {"type": "string"}})
    shut_tool = definition(properties={"q": {"type": "string"}}, additionalProperties=False)
    assert open_tool.check({"q": "x", "extra": 1}) == ""
    assert shut_tool.check({"q": "x", "extra": 1}) == "unknown argument 'extra'"
    assert shut_tool.check({"q": "x"}) == ""


def test_a_type_the_check_does_not_know_is_not_a_reason_to_refuse() -> None:
    assert definition(properties={"v": {"type": "null"}}).check({"v": 1}) == ""


# ------------------------------------------------------------------------ StageRecipe.tools
def recipe(**changes: Any) -> StageRecipe:
    fields: dict[str, Any] = {
        "stage": "research",
        "template": "research",
        "inputs": ("brief",),
        "max_output_tokens": 1000,
    }
    return StageRecipe(**{**fields, **changes})


def test_a_recipe_gives_a_stage_no_tools_unless_it_names_them() -> None:
    assert recipe().tools == ()
    assert recipe(tools=("web_search", "fetch_url")).tools == ("web_search", "fetch_url")


def test_a_recipes_tools_are_a_tuple_of_valid_unique_names() -> None:
    with pytest.raises(TypeError, match="tools are a tuple"):
        recipe(tools=["web_search"])
    with pytest.raises(ValueError, match="tools are tool names"):
        recipe(tools=("web search",))
    with pytest.raises(ValueError, match="tools are tool names"):
        recipe(tools=("",))
    with pytest.raises(ValueError, match="names each tool once"):
        recipe(tools=("web_search", "web_search"))


# ------------------------------------------------------------ tool_use in the call results
def test_a_tool_use_result_goes_with_its_calls_and_only_with_them() -> None:
    assert ModelCallResult("t", "tool_use", 5, False, (CALL,)).tool_calls == (CALL,)
    with pytest.raises(ValueError, match="tool_use goes with tool calls"):
        ModelCallResult("t", "tool_use", 5, False)
    with pytest.raises(ValueError, match="tool_use goes with tool calls"):
        ModelCallResult("t", "end_turn", 5, False, (CALL,))


def test_a_tool_use_result_can_be_a_replay_but_a_cut_off_one_cannot() -> None:
    assert ModelCallResult("t", "tool_use", 0, True, (CALL,)).replayed
    assert ModelCallResult("t", "end_turn", 0, True).replayed
    for reason in ("max_tokens", "refusal"):
        with pytest.raises(ValueError, match="a replay is free and always a complete answer"):
            ModelCallResult("t", reason, 0, True)


def test_a_replayed_tool_turn_cannot_have_cost() -> None:
    with pytest.raises(ValueError, match="a replay is free"):
        ModelCallResult("t", "tool_use", 5, True, (CALL,))


def test_only_a_complete_answer_can_ask_for_tools() -> None:
    assert ModelAnswer("", True, (), 5, 1, False, (CALL,)).tool_calls == (CALL,)
    assert ModelAnswer("t", True, (), 5, 1, False).tool_calls == ()
    with pytest.raises(ValueError, match="only a complete answer can ask for tools"):
        ModelAnswer("t", False, (ISSUE,), 5, 1, False, (CALL,))
