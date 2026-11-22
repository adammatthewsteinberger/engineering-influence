# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Both adapters speak tool use in their provider's format, and record and replay a tool conversation."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.cassettes.cassette_recording_transport import (
    CassetteRecordingTransport,
)
from engineering_influence.infrastructure.cassettes.cassette_redactor import CassetteRedactor
from engineering_influence.infrastructure.cassettes.cassette_replay_transport import (
    CassetteReplayTransport,
)
from engineering_influence.infrastructure.cassettes.json_cassette_store import JsonCassetteStore
from engineering_influence.infrastructure.models.anthropic_model import AnthropicModel
from engineering_influence.infrastructure.models.openai_compatible_model import (
    OpenAICompatibleModel,
)
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_turn import ModelTurn
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.tool_call import ToolCall
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_result import ToolResult

FIXTURES = Path(__file__).parent.parent / "fixtures" / "model_cassettes"
KEY = "sk-test-SECRETSECRET"
DESCRIPTOR = ProviderDescriptor(
    provider="fake",
    model="fake-1",
    family="fake",
    context_window=100_000,
    max_output_tokens=8_000,
    input_micro_usd_per_mtok=1_000_000,
    output_micro_usd_per_mtok=5_000_000,
    cache_read_micro_usd_per_mtok=100_000,
    cache_write_micro_usd_per_mtok=1_250_000,
    batch_discount_percent=50,
    price_effective="2026-11-01",
    usage_policy_url="https://example.test/policy",
)
SEARCH = ToolDefinition(
    "web_search",
    "Search the web.",
    {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
)
FETCH = ToolDefinition(
    "fetch_url", "Read a page.", {"type": "object", "properties": {"url": {"type": "string"}}}
)
PLAIN = ModelRequest("Be brief.", "Find the facts.", 300, "v1")
TOOLS = ModelRequest("Be brief.", "Find the facts.", 300, "v1", tools=(SEARCH, FETCH))


def asked(
    arguments: dict[str, Any] | None = None, call_id: str = "c1", name: str = "web_search"
) -> ToolCall:
    return ToolCall(call_id, name, arguments if arguments is not None else {"query": "bees"})


def after(turn: ModelTurn) -> ModelRequest:
    return ModelRequest(
        "Be brief.", "Find the facts.", 300, "v1", tools=(SEARCH, FETCH), transcript=(turn,)
    )


class Seen:
    """Answers every request with one body and keeps what it was sent."""

    def __init__(self, body: Any, status: int = 200) -> None:
        self.body, self.status = body, status
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status, json=self.body)

    def sent(self, index: int = -1) -> dict[str, Any]:
        loaded: dict[str, Any] = json.loads(self.requests[index].content)
        return loaded


def anthropic(seen: Callable[[httpx.Request], httpx.Response]) -> AnthropicModel:
    return AnthropicModel(httpx.Client(transport=httpx.MockTransport(seen)), KEY, DESCRIPTOR)


def openai(seen: Callable[[httpx.Request], httpx.Response]) -> OpenAICompatibleModel:
    return OpenAICompatibleModel(httpx.Client(transport=httpx.MockTransport(seen)), KEY, DESCRIPTOR)


def anthropic_reply(content: list[dict[str, Any]], stop: str = "end_turn") -> dict[str, Any]:
    usage = {"input_tokens": 10, "output_tokens": 5}
    return {"model": "claude-snap", "content": content, "stop_reason": stop, "usage": usage}


def openai_reply(message: dict[str, Any], finish: str = "stop") -> dict[str, Any]:
    usage = {"prompt_tokens": 10, "completion_tokens": 5}
    choice = {"index": 0, "message": message, "finish_reason": finish}
    return {"model": "gpt-snap", "choices": [choice], "usage": usage}


def unexpected(call: Callable[[], object]) -> str:
    with pytest.raises(ApplicationError) as error:
        call()
    assert (error.value.code, error.value.http_status) == ("MODEL_RESPONSE_UNEXPECTED", 502)
    return error.value.message


# ------------------------------------------------------------------ Anthropic: request
def test_anthropic_offers_each_tool_with_its_schema_and_nothing_else_changes() -> None:
    seen = Seen(anthropic_reply([{"type": "text", "text": "ok"}]))
    anthropic(seen).complete(TOOLS)
    body = seen.sent()
    assert body["tools"] == [
        {
            "name": "web_search",
            "description": "Search the web.",
            "input_schema": SEARCH.json_schema(),
        },
        {"name": "fetch_url", "description": "Read a page.", "input_schema": FETCH.json_schema()},
    ]
    assert body["messages"] == [{"role": "user", "content": "Find the facts."}]
    assert body["max_tokens"] == 300


def test_anthropic_sends_no_tools_key_when_none_are_offered() -> None:
    seen = Seen(anthropic_reply([{"type": "text", "text": "ok"}]))
    anthropic(seen).complete(PLAIN)
    assert "tools" not in seen.sent()


def test_anthropic_replays_a_finished_turn_as_tool_use_then_tool_result_blocks() -> None:
    turn = ModelTurn(
        "I will look that up.",
        (asked({"query": "bees"}, "c1"), asked({"url": "https://a.test"}, "c2", "fetch_url")),
        (ToolResult("c2", "page text"), ToolResult("c1", "no results", is_error=True)),
    )
    seen = Seen(anthropic_reply([{"type": "text", "text": "done"}]))
    anthropic(seen).complete(after(turn))
    assert seen.sent()["messages"] == [
        {"role": "user", "content": "Find the facts."},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "I will look that up."},
                {"type": "tool_use", "id": "c1", "name": "web_search", "input": {"query": "bees"}},
                {
                    "type": "tool_use",
                    "id": "c2",
                    "name": "fetch_url",
                    "input": {"url": "https://a.test"},
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "c1",
                    "content": "no results",
                    "is_error": True,
                },
                {"type": "tool_result", "tool_use_id": "c2", "content": "page text"},
            ],
        },
    ]


def test_anthropic_leaves_out_an_empty_text_block() -> None:
    turn = ModelTurn("  ", (asked(),), (ToolResult("c1", "r"),))
    seen = Seen(anthropic_reply([{"type": "text", "text": "done"}]))
    anthropic(seen).complete(after(turn))
    assistant = seen.sent()["messages"][1]["content"]
    assert [block["type"] for block in assistant] == ["tool_use"]


def test_anthropic_counts_tokens_for_the_same_tools_and_transcript() -> None:
    turn = ModelTurn("t", (asked(),), (ToolResult("c1", "r"),))
    seen = Seen({"input_tokens": 77})
    assert anthropic(seen).count_tokens(after(turn)) == 77
    body = seen.sent()
    assert [tool["name"] for tool in body["tools"]] == ["web_search", "fetch_url"]
    assert len(body["messages"]) == 3
    assert "max_tokens" not in body


# ----------------------------------------------------------------- Anthropic: response
def test_anthropic_maps_a_tool_use_reply_to_calls_and_the_tool_use_stop_reason() -> None:
    data = json.loads((FIXTURES / "anthropic" / "tool_use.json").read_text())["body"]
    response = anthropic(Seen(data)).complete(TOOLS)
    assert response.stop_reason == "tool_use"
    assert response.text == "I will look that up."
    assert response.calls == (ToolCall("toolu_01", "web_search", {"query": "bee colony size"}),)
    assert response.wants_tools()
    assert (response.usage.input_tokens, response.usage.output_tokens) == (150, 40)


def test_anthropic_keeps_every_call_in_order_and_joins_the_text_blocks() -> None:
    content = [
        {"type": "text", "text": "One. "},
        {"type": "tool_use", "id": "a", "name": "web_search", "input": {"query": "x"}},
        {"type": "text", "text": "Two."},
        {"type": "tool_use", "id": "b", "name": "fetch_url", "input": {}},
    ]
    response = anthropic(Seen(anthropic_reply(content, "tool_use"))).complete(TOOLS)
    assert response.text == "One. Two."
    assert [call.id for call in response.calls] == ["a", "b"]


def test_anthropic_refuses_a_tool_call_nobody_offered() -> None:
    content = [{"type": "tool_use", "id": "a", "name": "web_search", "input": {}}]
    message = unexpected(
        lambda: anthropic(Seen(anthropic_reply(content, "tool_use"))).complete(PLAIN)
    )
    assert "tool call that was not offered" in message


def test_anthropic_refuses_tool_use_with_no_call_and_a_call_with_the_wrong_stop_reason() -> None:
    unexpected(
        lambda: anthropic(
            Seen(anthropic_reply([{"type": "text", "text": "x"}], "tool_use"))
        ).complete(TOOLS)
    )
    call = [{"type": "tool_use", "id": "a", "name": "web_search", "input": {}}]
    unexpected(lambda: anthropic(Seen(anthropic_reply(call, "end_turn"))).complete(TOOLS))


@pytest.mark.parametrize(
    "block",
    [
        {"type": "tool_use", "id": "a", "name": "web_search", "input": "not an object"},
        {"type": "tool_use", "id": "a", "name": "web.search", "input": {}},
        {"type": "tool_use", "id": "a", "input": {}},
        {"type": "tool_use", "name": "web_search", "input": {}},
        {"type": "tool_use", "id": "a", "name": "web_search"},
    ],
)
def test_anthropic_refuses_a_malformed_tool_call(block: dict[str, Any]) -> None:
    unexpected(lambda: anthropic(Seen(anthropic_reply([block], "tool_use"))).complete(TOOLS))


# --------------------------------------------------------------- OpenAI-compatible: request
def test_openai_offers_each_tool_as_a_function() -> None:
    seen = Seen(openai_reply({"content": "ok"}))
    openai(seen).complete(TOOLS)
    assert seen.sent()["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web.",
                "parameters": SEARCH.json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_url",
                "description": "Read a page.",
                "parameters": FETCH.json_schema(),
            },
        },
    ]


def test_openai_sends_no_tools_key_when_none_are_offered() -> None:
    seen = Seen(openai_reply({"content": "ok"}))
    openai(seen).complete(PLAIN)
    assert "tools" not in seen.sent()


def test_openai_replays_a_finished_turn_as_an_assistant_message_then_tool_messages() -> None:
    turn = ModelTurn(
        "I will look that up.",
        (
            asked({"query": "bees", "n": 1}, "c1"),
            asked({"url": "https://a.test"}, "c2", "fetch_url"),
        ),
        (ToolResult("c2", "page text"), ToolResult("c1", "no results", is_error=True)),
    )
    seen = Seen(openai_reply({"content": "done"}))
    openai(seen).complete(after(turn))
    assert seen.sent()["messages"] == [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "Find the facts."},
        {
            "role": "assistant",
            "content": "I will look that up.",
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {"name": "web_search", "arguments": '{"n":1,"query":"bees"}'},
                },
                {
                    "id": "c2",
                    "type": "function",
                    "function": {"name": "fetch_url", "arguments": '{"url":"https://a.test"}'},
                },
            ],
        },
        {"role": "tool", "tool_call_id": "c1", "content": "Error: no results"},
        {"role": "tool", "tool_call_id": "c2", "content": "page text"},
    ]


def test_openai_sends_null_content_for_an_assistant_turn_with_no_text() -> None:
    turn = ModelTurn("", (asked(),), (ToolResult("c1", "r"),))
    seen = Seen(openai_reply({"content": "done"}))
    openai(seen).complete(after(turn))
    assert seen.sent()["messages"][2]["content"] is None


def test_openai_estimate_is_unchanged_without_tools_and_larger_with_them() -> None:
    model = openai(Seen({}))
    plain = model.count_tokens(PLAIN)
    assert plain == len("Be brief.") + len("Find the facts.") + 16
    with_tools = model.count_tokens(TOOLS)
    tools_json = json.dumps([[], model._tools(TOOLS)], ensure_ascii=False)
    assert with_tools == plain + len(tools_json.encode("utf-8"))


def test_openai_estimate_covers_the_calls_and_results_of_a_transcript() -> None:
    model = openai(Seen({}))
    turn = ModelTurn("caf\u00e9", (asked({"query": "bees"}),), (ToolResult("c1", "result text"),))
    plain, with_turn = model.count_tokens(TOOLS), model.count_tokens(after(turn))
    calls_json = json.dumps([model._messages(after(turn))[2]["tool_calls"]], ensure_ascii=False)
    expected_extra = (
        len("caf\u00e9".encode())
        + len("result text")
        + 2 * 8
        + len(calls_json.encode())
        - len("[]")
    )
    assert with_turn - plain == expected_extra


# ------------------------------------------------------------------ OpenAI-compatible: response
def test_openai_maps_a_tool_calls_reply() -> None:
    data = json.loads((FIXTURES / "openai_compatible" / "tool_use.json").read_text())["body"]
    response = openai(Seen(data)).complete(TOOLS)
    assert response.stop_reason == "tool_use"
    assert response.text == ""
    assert response.calls == (ToolCall("call_01", "web_search", {"query": "bee colony size"}),)
    assert (response.usage.input_tokens, response.usage.output_tokens) == (150, 40)


def test_openai_reads_arguments_given_as_an_object_or_left_empty() -> None:
    calls = [
        {
            "id": "a",
            "type": "function",
            "function": {"name": "web_search", "arguments": {"query": "x"}},
        },
        {"id": "b", "type": "function", "function": {"name": "fetch_url", "arguments": ""}},
    ]
    response = openai(
        Seen(openai_reply({"content": None, "tool_calls": calls}, "tool_calls"))
    ).complete(TOOLS)
    assert [(c.id, dict(c.arguments)) for c in response.calls] == [("a", {"query": "x"}), ("b", {})]


def test_openai_treats_a_stop_that_comes_with_tool_calls_as_tool_use() -> None:
    call = {"id": "a", "type": "function", "function": {"name": "web_search", "arguments": "{}"}}
    response = openai(Seen(openai_reply({"content": "", "tool_calls": [call]}, "stop"))).complete(
        TOOLS
    )
    assert (response.stop_reason, len(response.calls)) == ("tool_use", 1)


def test_openai_keeps_a_length_stop_that_comes_with_tool_calls_as_what_it_is() -> None:
    call = {"id": "a", "type": "function", "function": {"name": "web_search", "arguments": "{}"}}
    unexpected(
        lambda: openai(
            Seen(openai_reply({"content": "", "tool_calls": [call]}, "length"))
        ).complete(TOOLS)
    )


def test_openai_refuses_a_tool_call_nobody_offered() -> None:
    call = {"id": "a", "type": "function", "function": {"name": "web_search", "arguments": "{}"}}
    message = unexpected(
        lambda: openai(
            Seen(openai_reply({"content": "", "tool_calls": [call]}, "tool_calls"))
        ).complete(PLAIN)
    )
    assert "tool call that was not offered" in message


def test_openai_refuses_tool_calls_finish_with_no_calls() -> None:
    unexpected(lambda: openai(Seen(openai_reply({"content": "x"}, "tool_calls"))).complete(TOOLS))


@pytest.mark.parametrize(
    "function",
    [
        {"name": "web_search", "arguments": "{not json"},
        {"name": "web_search", "arguments": "[1, 2]"},
        {"name": "web_search", "arguments": 5},
        {"name": "web.search", "arguments": "{}"},
        {"arguments": "{}"},
        {"name": "web_search"},
    ],
)
def test_openai_refuses_a_malformed_tool_call(function: dict[str, Any]) -> None:
    call = {"id": "a", "type": "function", "function": function}
    unexpected(
        lambda: openai(
            Seen(openai_reply({"content": "", "tool_calls": [call]}, "tool_calls"))
        ).complete(TOOLS)
    )


def test_openai_refuses_a_call_with_no_id() -> None:
    call = {"type": "function", "function": {"name": "web_search", "arguments": "{}"}}
    unexpected(
        lambda: openai(
            Seen(openai_reply({"content": "", "tool_calls": [call]}, "tool_calls"))
        ).complete(TOOLS)
    )


# ----------------------------------------------------- record and replay a tool conversation
def test_a_two_step_tool_conversation_records_once_and_replays_the_same(tmp_path: Path) -> None:
    first = json.loads((FIXTURES / "anthropic" / "tool_use.json").read_text())["body"]
    second = anthropic_reply([{"type": "text", "text": "Colonies hold tens of thousands of bees."}])
    answers = [first, second]

    def provider(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=answers.pop(0))

    store = JsonCassetteStore(tmp_path, CassetteRedactor([KEY]))
    recorder = CassetteRecordingTransport(
        httpx.MockTransport(provider), CassetteRedactor([KEY]), store
    )

    def conversation(model: AnthropicModel) -> tuple[ModelResponse, ModelResponse]:
        asked_for = model.complete(TOOLS)
        turn = ModelTurn(
            asked_for.text,
            asked_for.calls,
            (ToolResult(asked_for.calls[0].id, "Colonies: 20,000 to 80,000."),),
        )
        return asked_for, model.complete(after(turn))

    live = conversation(AnthropicModel(httpx.Client(transport=recorder), KEY, DESCRIPTOR))
    recorder.finish(
        "tool-conversation", "anthropic", "synthetic; fixture stands in for the provider"
    )
    replay = CassetteReplayTransport(store.load("tool-conversation"), CassetteRedactor([KEY]))
    assert conversation(AnthropicModel(httpx.Client(transport=replay), KEY, DESCRIPTOR)) == live
    replay.finish()
    assert live[0].stop_reason == "tool_use" and live[1].stop_reason == "end_turn"


def test_changing_a_tool_after_recording_fails_the_replay_loudly(tmp_path: Path) -> None:
    body = anthropic_reply([{"type": "text", "text": "done"}])
    store = JsonCassetteStore(tmp_path, CassetteRedactor([KEY]))
    recorder = CassetteRecordingTransport(
        httpx.MockTransport(Seen(body)), CassetteRedactor([KEY]), store
    )
    AnthropicModel(httpx.Client(transport=recorder), KEY, DESCRIPTOR).complete(TOOLS)
    recorder.finish("one-call", "anthropic")
    changed = ModelRequest("Be brief.", "Find the facts.", 300, "v1", tools=(SEARCH,))
    replay = CassetteReplayTransport(store.load("one-call"), CassetteRedactor([KEY]))
    with pytest.raises(ApplicationError) as error:
        AnthropicModel(httpx.Client(transport=replay), KEY, DESCRIPTOR).complete(changed)
    assert error.value.code == "CASSETTE_MISMATCH"
    assert "differs in: tools" in error.value.message
    assert not isinstance(error.value, TransientStageError)


def test_openai_estimate_copes_with_an_assistant_turn_that_has_no_text() -> None:
    model = openai(Seen({}))
    turn = ModelTurn("", (asked(),), (ToolResult("c1", "r"),))
    assert model.count_tokens(after(turn)) > model.count_tokens(TOOLS)


def test_anthropic_still_refuses_a_stop_reason_it_does_not_know() -> None:
    body = anthropic_reply([{"type": "text", "text": "x"}], "pause_turn")
    assert "stop reason 'pause_turn'" in unexpected(lambda: anthropic(Seen(body)).complete(TOOLS))


def test_openai_still_refuses_a_finish_reason_it_does_not_know() -> None:
    body = openai_reply({"content": "x"}, "function_call")
    assert "finish reason 'function_call'" in unexpected(lambda: openai(Seen(body)).complete(TOOLS))
