# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""CallModel journals a tool turn whole, replays it for nothing, and keys it by the conversation."""

import hashlib
import json
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.budget import Budget
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_turn import ModelTurn
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.tool_call import ToolCall
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_result import ToolResult
from engineering_influence.services.call_model import CallModel
from engineering_influence.services.spend_guard import SpendGuard

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
USAGE = ModelUsage(100, 50)
COST = DESCRIPTOR.cost_micro_usd(USAGE)
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


def turn(
    text: str = "t", call: ToolCall | None = None, content: str = "r", error: bool = False
) -> ModelTurn:
    made = call or asked()
    return ModelTurn(text, (made,), (ToolResult(made.id, content, error),))


def after(*turns: ModelTurn, tools: tuple[ToolDefinition, ...] = (SEARCH, FETCH)) -> ModelRequest:
    return ModelRequest("Be brief.", "Find the facts.", 300, "v1", tools=tools, transcript=turns)


def said(text: str = "done", *calls: ToolCall, stop: str | None = None) -> ModelResponse:
    reason = stop or ("tool_use" if calls else "end_turn")
    return ModelResponse(text, USAGE, "fake-1-snap", reason, calls)


class Script(ModelInterface):
    """Answers each request from a script, and keeps what it was asked."""

    def __init__(self, *responses: ModelResponse) -> None:
        self.responses = list(responses)
        self.requests: list[ModelRequest] = []

    def describe(self) -> ProviderDescriptor:
        return DESCRIPTOR

    def availability(self) -> ModelAvailability:
        return ModelAvailability.AVAILABLE

    def count_tokens(self, request: ModelRequest) -> int:
        return 10

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        return self.responses.pop(0)


class World:
    def __init__(self, *responses: ModelResponse) -> None:
        self.model = Script(*responses)
        self.journal = InMemoryJournal()
        self.guard = SpendGuard(Budget(cap=10_000_000))
        self.service = CallModel(self.model, self.journal)

    def call(self, request: ModelRequest) -> Any:
        return self.service.call(self.guard, "run-1", "stage", 1, request)


def test_a_tool_turn_is_journaled_with_its_text_and_calls_and_costs_what_it_cost() -> None:
    world = World(said("looking", asked()))
    result = world.call(TOOLS)
    assert (result.text, result.stop_reason, result.replayed) == ("looking", "tool_use", False)
    assert result.tool_calls == (asked(),)
    assert result.cost_micro_usd == COST > 0
    [entry] = world.journal.entries("run-1")
    assert entry.cost_micro_usd == COST
    assert json.loads(entry.response) == {
        "text": "looking",
        "calls": [{"id": "c1", "name": "web_search", "arguments": {"query": "bees"}}],
    }
    assert world.guard.budget().spent == COST


def test_the_same_tool_turn_is_replayed_for_nothing_with_its_calls() -> None:
    world = World(said("looking", asked()))
    first = world.call(TOOLS)
    again = world.call(TOOLS)
    assert (again.text, again.stop_reason) == (first.text, "tool_use")
    assert again.tool_calls == first.tool_calls
    assert (again.replayed, again.cost_micro_usd) == (True, 0)
    assert len(world.model.requests) == 1
    assert len(world.journal.entries("run-1")) == 1
    assert world.guard.budget().spent == COST


def test_a_final_answer_to_a_request_with_tools_is_replayed_too() -> None:
    world = World(said("the answer"))
    first = world.call(TOOLS)
    again = world.call(TOOLS)
    assert (first.stop_reason, again.stop_reason) == ("end_turn", "end_turn")
    assert (again.text, again.tool_calls, again.replayed) == ("the answer", (), True)
    assert len(world.model.requests) == 1


def test_replay_finds_a_tool_turn_without_asking_the_model() -> None:
    world = World(said("looking", asked()))
    assert world.service.replay("run-1", "stage", TOOLS) is None
    world.call(TOOLS)
    found = world.service.replay("run-1", "stage", TOOLS)
    assert found is not None and found.tool_calls == (asked(),)
    assert len(world.model.requests) == 1


def test_text_with_accents_and_symbols_comes_back_exactly() -> None:
    world = World(said("café ☕ — «ça»", asked({"query": "abeilles à miel"})))
    first = world.call(TOOLS)
    again = world.call(TOOLS)
    assert again.text == first.text == "café ☕ — «ça»"
    assert again.tool_calls[0].arguments == {"query": "abeilles à miel"}


def test_a_request_with_tools_is_a_different_request_from_the_same_words_without() -> None:
    world = World(said("plain"), said("with tools"))
    assert world.call(PLAIN).text == "plain"
    assert world.call(TOOLS).text == "with tools"
    assert world.call(PLAIN).replayed and world.call(TOOLS).replayed
    assert len(world.model.requests) == 2
    keys = {entry.key.digest() for entry in world.journal.entries("run-1")}
    assert len(keys) == 2


def test_a_plain_request_is_stored_and_keyed_exactly_as_it_was_before_tools() -> None:
    world = World(said("just text"))
    world.call(PLAIN)
    [entry] = world.journal.entries("run-1")
    assert entry.response == "just text"
    context = json.dumps(["Be brief.", "Find the facts."], sort_keys=True)
    assert entry.key.context_hash == hashlib.sha256(context.encode("utf-8")).hexdigest()
    params = hashlib.sha256(b"max_output_tokens=300").hexdigest()
    assert (entry.key.params_hash, entry.key.prompt_version) == (params, "v1")


def test_every_part_of_the_conversation_so_far_is_part_of_the_key() -> None:
    variants = {
        "none": TOOLS,
        "base": after(turn()),
        "text": after(turn(text="other")),
        "call arguments": after(turn(call=asked({"query": "wasps"}))),
        "call id": after(turn(call=asked(call_id="c2"))),
        "call name": after(turn(call=asked(name="fetch_url"))),
        "result": after(turn(content="other")),
        "error flag": after(turn(error=True)),
        "two turns": after(turn(), turn(call=asked(call_id="c9"))),
    }
    world = World(*[said(f"answer {name}") for name in variants])
    for name, request in variants.items():
        assert world.call(request).text == f"answer {name}"
    assert len(world.model.requests) == len(variants)
    for name, request in variants.items():
        again = world.call(request)
        assert (again.text, again.replayed) == (f"answer {name}", True)
    assert len(world.model.requests) == len(variants)


def test_the_tools_offered_are_part_of_the_key() -> None:
    reworded = ToolDefinition("web_search", "Search the web today.", dict(SEARCH.parameters))
    narrower = ToolDefinition(
        "web_search", "Search the web.", {"type": "object", "properties": {"q": {"type": "string"}}}
    )
    variants = {
        "both": after(turn()),
        "only search": after(turn(), tools=(SEARCH,)),
        "reworded": after(turn(), tools=(reworded, FETCH)),
        "schema": after(turn(), tools=(narrower, FETCH)),
    }
    world = World(*[said(name) for name in variants])
    for name, request in variants.items():
        assert world.call(request).text == name
    assert len(world.model.requests) == len(variants)


def test_a_cut_off_tool_turn_is_journaled_for_its_cost_but_never_replayed() -> None:
    world = World(said("cu", stop="max_tokens"))
    result = world.call(TOOLS)
    assert (result.stop_reason, result.tool_calls, result.replayed) == ("max_tokens", (), False)
    assert result.cost_micro_usd == COST
    assert len(world.journal.entries("run-1")) == 1
    assert world.service.replay("run-1", "stage", TOOLS) is None


def test_a_model_that_calls_a_tool_when_none_was_offered_is_billed_and_refused() -> None:
    world = World(said("sneaky", asked()), said("fine"))
    with pytest.raises(ApplicationError) as error:
        world.call(PLAIN)
    assert (error.value.code, error.value.http_status) == ("MODEL_RESPONSE_UNEXPECTED", 502)
    assert error.value.message == "the model asked for tools that were not offered"
    assert world.guard.budget().spent == COST
    [entry] = world.journal.entries("run-1")
    assert entry.cost_micro_usd == COST
    assert world.service.replay("run-1", "stage", PLAIN) is None
    assert world.call(PLAIN).text == "fine"
