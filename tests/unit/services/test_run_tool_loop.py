# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""RunToolLoop: ask, run the tools the model calls, ask again, and stop at the limits."""

from collections.abc import Collection, Sequence
from typing import Any

from engineering_influence.models.budget import Budget
from engineering_influence.models.model_answer import ModelAnswer
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_turn import ModelTurn
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.tool_call import ToolCall
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_loop_limits import ToolLoopLimits
from engineering_influence.models.tool_result import ToolResult
from engineering_influence.services.interfaces.ask_model_interface import AskModelInterface
from engineering_influence.services.interfaces.run_tool_loop_interface import (
    RunToolLoopInterface,
)
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface
from engineering_influence.services.interfaces.tool_runner_interface import ToolRunnerInterface
from engineering_influence.services.run_tool_loop import RunToolLoop
from engineering_influence.services.spend_guard import SpendGuard

SEARCH = ToolDefinition(
    "web_search", "Search.", {"type": "object", "properties": {"query": {"type": "string"}}}
)
FETCH = ToolDefinition("fetch_url", "Read.", {"type": "object"})
REQUEST = ModelRequest("sys", "prompt", 500, "v1", tools=(SEARCH, FETCH))
PLAIN = ModelRequest("sys", "prompt", 500, "v1")


def call(call_id: str = "c1", name: str = "web_search") -> ToolCall:
    return ToolCall(call_id, name, {"query": call_id})


def asks(text: str = "", *calls: ToolCall, cost: int = 10, made: int = 1) -> ModelAnswer:
    return ModelAnswer(text, True, (), cost, made, False, calls)


def cut(text: str = "half", cost: int = 7, made: int = 2) -> ModelAnswer:
    issue = QualityIssue("research", "TRUNCATED", "ran out of room", blocking=True)
    return ModelAnswer(text, False, (issue,), cost, made, False)


class Asker(AskModelInterface):
    def __init__(self, *answers: ModelAnswer, forever: ModelAnswer | None = None) -> None:
        self.answers = list(answers)
        self.forever = forever
        self.calls: list[tuple[SpendGuardInterface, str, str, int, ModelRequest]] = []

    def ask(
        self,
        guard: SpendGuardInterface,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ModelAnswer:
        self.calls.append((guard, run_id, stage, attempt, request))
        if self.answers:
            return self.answers.pop(0)
        assert self.forever is not None
        return self.forever


class Runner(ToolRunnerInterface):
    def __init__(self) -> None:
        self.calls: list[
            tuple[str, str, int, ToolCall, tuple[str, ...], str, tuple[ModelTurn, ...]]
        ] = []

    def run(
        self,
        run_id: str,
        stage: str,
        attempt: int,
        call: ToolCall,
        offered: Collection[str],
        prompt: str,
        transcript: Sequence[ModelTurn],
    ) -> ToolResult:
        self.calls.append((run_id, stage, attempt, call, tuple(offered), prompt, tuple(transcript)))
        return ToolResult(call.id, f"result for {call.id}")

    def close(self) -> None:
        pass


class World:
    def __init__(
        self,
        *answers: ModelAnswer,
        forever: ModelAnswer | None = None,
        limits: ToolLoopLimits | None = None,
    ) -> None:
        self.asker = Asker(*answers, forever=forever)
        self.runner = Runner()
        self.guard = SpendGuard(Budget(cap=1_000_000))
        self.loop = RunToolLoop(self.asker, self.runner, limits or ToolLoopLimits())

    def run(self, request: ModelRequest = REQUEST) -> Any:
        return self.loop.run(self.guard, "run-1", "research", 2, request)

    def sent(self, index: int) -> ModelRequest:
        return self.asker.calls[index][4]


def test_it_is_a_tool_loop() -> None:
    assert isinstance(World().loop, RunToolLoopInterface)


def test_a_model_that_asks_for_no_tools_is_one_turn() -> None:
    world = World(asks("the answer", cost=33, made=3))
    result = world.run()
    assert (result.text, result.complete, result.issues) == ("the answer", True, ())
    assert (result.cost_micro_usd, result.model_calls, result.tool_calls) == (33, 3, 0)
    assert (result.turns, result.transcript, result.used_tools()) == (1, (), False)
    assert world.runner.calls == []


def test_a_request_with_no_tools_goes_through_the_same_loop_in_one_turn() -> None:
    world = World(asks("plain text"))
    assert world.run(PLAIN).text == "plain text"
    assert world.sent(0) == PLAIN


def test_the_run_stage_attempt_and_guard_reach_the_asker_and_the_runner() -> None:
    world = World(asks("", call()), asks("done"))
    world.run()
    for guard, run_id, stage, attempt, _ in world.asker.calls:
        assert (guard, run_id, stage, attempt) == (world.guard, "run-1", "research", 2)
    assert world.runner.calls[0][:3] == ("run-1", "research", 2)


def test_a_tool_round_is_run_and_the_next_request_carries_what_came_back() -> None:
    world = World(asks("let me look", call("c1"), cost=10), asks("final", cost=5, made=2))
    result = world.run()
    expected = ModelTurn("let me look", (call("c1"),), (ToolResult("c1", "result for c1"),))
    assert world.sent(0) == REQUEST
    assert world.sent(1).transcript == (expected,)
    assert (world.sent(1).system, world.sent(1).tools) == ("sys", (SEARCH, FETCH))
    assert (result.text, result.complete, result.turns) == ("final", True, 2)
    assert (result.cost_micro_usd, result.model_calls, result.tool_calls) == (15, 3, 1)
    assert result.transcript == (expected,)
    assert result.used_tools()


def test_the_runner_is_told_which_tools_the_stage_was_offered() -> None:
    world = World(asks("", call()), asks("done"))
    world.run()
    assert world.runner.calls[0][4] == ("web_search", "fetch_url")


def test_every_call_of_a_turn_runs_in_order_and_each_result_goes_with_its_call() -> None:
    world = World(asks("", call("a"), call("b", "fetch_url"), call("c")), asks("done"))
    result = world.run()
    assert [c[3].id for c in world.runner.calls] == ["a", "b", "c"]
    [turn] = result.transcript
    assert [r.call_id for r in turn.results] == ["a", "b", "c"]
    assert result.tool_calls == 3


def test_a_conversation_already_under_way_is_carried_on_not_restarted() -> None:
    earlier = ModelTurn("t", (call("old"),), (ToolResult("old", "r"),))
    resumed = ModelRequest("sys", "prompt", 500, "v1", tools=(SEARCH,), transcript=(earlier,))
    world = World(asks("", call("new")), asks("done"))
    result = world.run(resumed)
    assert world.sent(0).transcript == (earlier,)
    assert [t.calls[0].id for t in world.sent(1).transcript] == ["old", "new"]
    assert [t.calls[0].id for t in result.transcript] == ["old", "new"]


def test_the_callers_request_is_not_changed() -> None:
    world = World(asks("", call()), asks("done"))
    world.run()
    assert REQUEST.transcript == ()


def test_an_answer_that_is_cut_off_ends_the_loop_with_its_issues_and_what_it_had() -> None:
    world = World(asks("", call("c1")), cut("half an ans", cost=7, made=2))
    result = world.run()
    assert (result.text, result.complete) == ("half an ans", False)
    assert [i.code for i in result.issues] == ["TRUNCATED"]
    assert (result.cost_micro_usd, result.model_calls, result.turns) == (17, 3, 2)
    assert len(result.transcript) == 1


def test_a_first_answer_that_is_cut_off_runs_no_tools() -> None:
    world = World(cut())
    result = world.run()
    assert (result.complete, result.turns, result.tool_calls) == (False, 1, 0)
    assert world.runner.calls == []


def test_a_model_that_never_stops_asking_is_stopped_at_the_turn_limit() -> None:
    world = World(forever=asks("", call()), limits=ToolLoopLimits(max_turns=3))
    result = world.run()
    [issue] = result.issues
    assert (issue.stage, issue.code, issue.blocking) == ("research", "TOOL_LOOP_EXHAUSTED", True)
    assert issue.detail == "the model was still asking for tools after 3 turns"
    assert (result.text, result.complete, result.turns) == ("", False, 3)
    assert len(world.asker.calls) == 3
    assert len(world.runner.calls) == 3
    assert (result.cost_micro_usd, result.model_calls, result.tool_calls) == (30, 3, 3)
    assert len(result.transcript) == 3


def test_a_model_that_wants_one_more_round_than_it_gets_is_stopped_after_that_round() -> None:
    world = World(asks("", call("a")), asks("", call("b")), limits=ToolLoopLimits(max_turns=2))
    result = world.run()
    assert [i.code for i in result.issues] == ["TOOL_LOOP_EXHAUSTED"]
    assert (result.turns, len(world.asker.calls), len(world.runner.calls)) == (2, 2, 2)


def test_a_call_past_the_tool_limit_is_not_run_and_the_model_is_told_to_answer() -> None:
    world = World(
        asks("", call("a"), call("b"), call("c")),
        asks("", call("d")),
        asks("done"),
        limits=ToolLoopLimits(max_tool_calls=2),
    )
    result = world.run()
    assert [c[3].id for c in world.runner.calls] == ["a", "b"]
    first, second = result.transcript
    assert first.result_for("c") == ToolResult(
        "c", "no more tool calls are allowed; answer with what you have", True
    )
    assert second.result_for("d").is_error
    assert (result.tool_calls, result.complete, result.text) == (2, True, "done")


def test_exactly_the_limit_of_calls_all_run() -> None:
    world = World(
        asks("", call("a"), call("b")), asks("done"), limits=ToolLoopLimits(max_tool_calls=2)
    )
    result = world.run()
    assert [c[3].id for c in world.runner.calls] == ["a", "b"]
    assert not any(r.is_error for r in result.transcript[0].results)


def test_the_runner_is_given_the_prompt_and_the_conversation_so_far() -> None:
    world = World(asks("", call("a")), asks("", call("b"), call("c")), asks("done"))
    world.run()
    first, second, third = world.runner.calls
    assert (first[5], first[6]) == ("prompt", ())
    assert [turn.calls[0].id for turn in second[6]] == ["a"]
    assert third[6] == second[6]  # calls in one turn see the same conversation, not each other
    assert second[5] == third[5] == "prompt"


def test_a_conversation_carried_over_is_what_the_runner_is_given() -> None:
    earlier = ModelTurn("t", (call("old"),), (ToolResult("old", "an old result"),))
    resumed = ModelRequest("sys", "prompt", 500, "v1", tools=(SEARCH,), transcript=(earlier,))
    world = World(asks("", call("new")), asks("done"))
    world.run(resumed)
    assert world.runner.calls[0][6] == (earlier,)
