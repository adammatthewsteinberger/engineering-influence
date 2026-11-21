# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ToolDefinition, ToolCall, ToolResult, ModelTurn, and the tool fields of the request and response."""

from typing import Any

import pytest

from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_turn import ModelTurn
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.tool_call import ToolCall
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_result import ToolResult

SCHEMA = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}


def tool(**changes: Any) -> ToolDefinition:
    values: dict[str, Any] = {
        "name": "web_search",
        "description": "Search the web.",
        "parameters": SCHEMA,
    }
    values.update(changes)
    return ToolDefinition(**values)


@pytest.mark.parametrize("name", ["", "a b", "a.b", "a/b", "caf\u00e9", "x" * 65])
def test_a_tool_name_must_be_what_the_providers_accept(name: str) -> None:
    with pytest.raises(ValueError, match="tool name"):
        tool(name=name)


@pytest.mark.parametrize("name", ["a", "web_search", "Web-Search_2", "x" * 64])
def test_a_tool_name_in_range_is_accepted(name: str) -> None:
    assert tool(name=name).name == name


def test_a_tool_needs_a_description_and_object_parameters_that_are_plain_json() -> None:
    with pytest.raises(ValueError, match="description"):
        tool(description="  ")
    for bad in ({}, {"type": "string"}, [], "object", None):
        with pytest.raises(ValueError, match="type object"):
            tool(parameters=bad)
    with pytest.raises(ValueError, match="plain JSON"):
        tool(parameters={"type": "object", "default": {1, 2}})


def test_the_schema_a_tool_hands_out_is_a_copy() -> None:
    held = tool()
    expected = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }
    copy = held.json_schema()
    assert copy == expected
    copy["properties"]["query"]["type"] = "number"
    copy["extra"] = True
    assert held.json_schema() == expected
    assert held.parameters == expected


def call(**changes: Any) -> ToolCall:
    values: dict[str, Any] = {"id": "call_1", "name": "web_search", "arguments": {"query": "bees"}}
    values.update(changes)
    return ToolCall(**values)


def test_a_call_needs_an_id_a_valid_tool_name_and_json_object_arguments() -> None:
    with pytest.raises(ValueError, match="id"):
        call(id=" ")
    with pytest.raises(ValueError, match="names a tool"):
        call(name="a.b")
    with pytest.raises(TypeError, match="JSON object"):
        call(arguments=["query"])
    with pytest.raises(ValueError, match="plain JSON"):
        call(arguments={"query": object()})


def test_the_arguments_are_written_the_same_way_every_time() -> None:
    first = call(arguments={"b": 1, "a": {"y": 2, "x": "caf\u00e9"}})
    second = call(arguments={"a": {"x": "caf\u00e9", "y": 2}, "b": 1})
    assert (
        first.arguments_json() == second.arguments_json() == '{"a":{"x":"caf\u00e9","y":2},"b":1}'
    )
    assert call(arguments={}).arguments_json() == "{}"


def test_a_result_answers_a_call_by_its_id_and_may_be_an_error() -> None:
    assert ToolResult("call_1", "found").is_error is False
    assert ToolResult("call_1", "boom", is_error=True).is_error is True
    with pytest.raises(ValueError, match="id"):
        ToolResult(" ", "x")


def test_a_result_within_the_limit_is_returned_as_it_is() -> None:
    result = ToolResult("c", "12345")
    assert result.capped(5) is result
    assert result.capped(100) is result


def test_a_longer_result_is_cut_with_a_note_of_how_much() -> None:
    capped = ToolResult("c", "1234567890", is_error=True).capped(4)
    assert capped == ToolResult("c", "1234\n[truncated: 6 more characters]", is_error=True)


@pytest.mark.parametrize("limit", [0, -1])
def test_a_result_limit_is_at_least_one(limit: int) -> None:
    with pytest.raises(ValueError, match="at least one"):
        ToolResult("c", "x").capped(limit)


def turn(
    calls: tuple[ToolCall, ...] | None = None,
    results: tuple[ToolResult, ...] | None = None,
    text: str = "Looking.",
) -> ModelTurn:
    held = calls if calls is not None else (call(),)
    answers = (
        results if results is not None else tuple(ToolResult(c.id, f"result {c.id}") for c in held)
    )
    return ModelTurn(text, held, answers)


def test_a_turn_pairs_every_call_with_exactly_one_result() -> None:
    held = turn()
    assert held.result_for("call_1") == ToolResult("call_1", "result call_1")


def test_results_may_come_in_any_order() -> None:
    calls = (call(id="a"), call(id="b"))
    held = turn(calls, (ToolResult("b", "second"), ToolResult("a", "first")))
    assert held.result_for("a").content == "first"
    assert held.result_for("b").content == "second"


def test_a_turn_refuses_calls_and_results_that_do_not_match() -> None:
    with pytest.raises(ValueError, match="at least one tool"):
        turn(calls=())
    with pytest.raises(ValueError, match="at least one tool"):
        turn(calls=[call()])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="results are a tuple"):
        turn(results=[ToolResult("call_1", "x")])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="different ids"):
        turn(
            calls=(call(id="a"), call(id="a")), results=(ToolResult("a", "x"), ToolResult("a", "y"))
        )
    with pytest.raises(ValueError, match="exactly one result"):
        turn(calls=(call(id="a"), call(id="b")), results=(ToolResult("a", "x"),))
    with pytest.raises(ValueError, match="exactly one result"):
        turn(calls=(call(id="a"),), results=(ToolResult("a", "x"), ToolResult("z", "y")))
    with pytest.raises(ValueError, match="exactly one result"):
        turn(calls=(call(id="a"),), results=(ToolResult("a", "x"), ToolResult("a", "y")))


def test_asking_for_a_result_of_a_call_the_turn_did_not_make_is_an_error() -> None:
    with pytest.raises(ValueError, match="no call 'zzz'"):
        turn().result_for("zzz")


def request(**changes: Any) -> ModelRequest:
    values: dict[str, Any] = {
        "system": "s",
        "prompt": "p",
        "max_output_tokens": 10,
        "prompt_version": "v1",
    }
    values.update(changes)
    return ModelRequest(**values)


def test_a_request_has_no_tools_and_no_transcript_unless_given() -> None:
    plain = request()
    assert (plain.tools, plain.transcript) == ((), ())
    with_tools = request(tools=(tool(),), transcript=(turn(),))
    assert (len(with_tools.tools), len(with_tools.transcript)) == (1, 1)


def test_a_request_refuses_tools_it_cannot_make_sense_of() -> None:
    with pytest.raises(TypeError, match="tuples"):
        request(tools=[tool()])
    with pytest.raises(TypeError, match="tuples"):
        request(tools=(tool(),), transcript=[turn()])
    with pytest.raises(ValueError, match="each tool once"):
        request(tools=(tool(), tool()))
    with pytest.raises(ValueError, match="goes with the tools"):
        request(transcript=(turn(),))


def response(**changes: Any) -> ModelResponse:
    values: dict[str, Any] = {
        "text": "t",
        "usage": ModelUsage(1, 1),
        "model_snapshot": "m",
        "stop_reason": "end_turn",
    }
    values.update(changes)
    return ModelResponse(**values)


def test_tool_use_goes_with_tool_calls_and_only_with_them() -> None:
    wants = response(stop_reason="tool_use", calls=(call(),))
    assert wants.wants_tools() is True
    assert response().wants_tools() is False
    with pytest.raises(ValueError, match="tool_use goes with tool calls"):
        response(stop_reason="tool_use")
    for reason in ("end_turn", "max_tokens", "refusal"):
        with pytest.raises(ValueError, match="tool_use goes with tool calls"):
            response(stop_reason=reason, calls=(call(),))


def test_the_calls_in_one_response_have_different_ids() -> None:
    with pytest.raises(ValueError, match="different ids"):
        response(stop_reason="tool_use", calls=(call(id="a"), call(id="a")))
    assert response(stop_reason="tool_use", calls=(call(id="a"), call(id="b"))).wants_tools()


def test_a_tool_use_response_is_neither_truncated_nor_refused() -> None:
    wants = response(stop_reason="tool_use", calls=(call(),))
    assert (wants.was_truncated(), wants.was_refused()) == (False, False)
