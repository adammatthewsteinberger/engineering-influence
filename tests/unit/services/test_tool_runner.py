# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ToolRunner: only offered tools run, bad arguments are caught, and a call is made once."""

import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.tool_call import ToolCall
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_loop_limits import ToolLoopLimits
from engineering_influence.models.tool_result import ToolResult
from engineering_influence.services.interfaces.tool_runner_interface import ToolRunnerInterface
from engineering_influence.services.tool_registry import ToolRegistry
from engineering_influence.services.tool_runner import ToolRunner


class Echo(ToolInterface):
    """Says back what it was given; can be told to fail or to wait."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.fail: BaseException | None = None
        self.block: threading.Event | None = None

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            "echo",
            "Echo it.",
            {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        )

    def invoke(self, arguments: Mapping[str, Any]) -> str:
        self.calls.append(dict(arguments))
        if self.block is not None:
            self.block.wait(10)
        if self.fail is not None:
            raise self.fail
        return f"echo: {arguments['text']}"


class World:
    def __init__(self, limits: ToolLoopLimits | None = None, workers: int = 4) -> None:
        self.tool = Echo()
        self.journal = InMemoryJournal()
        self.runner = ToolRunner(
            ToolRegistry((self.tool,)), self.journal, limits or ToolLoopLimits(), workers
        )

    def run(
        self,
        call: ToolCall,
        offered: tuple[str, ...] = ("echo",),
        run_id: str = "run-1",
        stage: str = "research",
    ) -> ToolResult:
        return self.runner.run(run_id, stage, 1, call, offered)


@contextmanager
def made(limits: ToolLoopLimits | None = None) -> Iterator[World]:
    world = World(limits)
    try:
        yield world
    finally:
        world.runner.close()


def say(text: str = "hi", call_id: str = "c1", name: str = "echo") -> ToolCall:
    return ToolCall(call_id, name, {"text": text})


def test_it_is_a_tool_runner() -> None:
    with made() as world:
        assert isinstance(world.runner, ToolRunnerInterface)


def test_an_offered_tool_runs_and_answers_the_call_by_its_id() -> None:
    with made() as world:
        assert world.run(say("hi", "call-7")) == ToolResult("call-7", "echo: hi")
        assert world.tool.calls == [{"text": "hi"}]


def test_a_tool_the_stage_was_not_given_runs_nothing_even_when_it_exists() -> None:
    with made() as world:
        result = world.run(say(), offered=("other",))
        assert result == ToolResult("c1", "no tool named 'echo' is available here", True)
        assert world.tool.calls == []
        assert world.journal.entries("run-1") == []


def test_a_tool_nobody_registered_runs_nothing() -> None:
    with made() as world:
        result = world.run(say(name="ghost"), offered=("ghost",))
        assert result == ToolResult("c1", "no tool named 'ghost' is available here", True)
        assert world.journal.entries("run-1") == []


def test_arguments_that_do_not_fit_are_answered_with_what_is_wrong_and_run_nothing() -> None:
    with made() as world:
        result = world.run(ToolCall("c1", "echo", {}))
        assert result == ToolResult(
            "c1", "invalid arguments: missing the required argument 'text'", True
        )
        wrong = world.run(ToolCall("c2", "echo", {"text": 5}))
        assert wrong.content == "invalid arguments: argument 'text' must be of type string"
        assert world.tool.calls == []
        assert world.journal.entries("run-1") == []


def test_the_same_call_is_made_once_and_replayed_under_the_current_call_id() -> None:
    with made() as world:
        first = world.run(say("hi", "c1"))
        again = world.run(say("hi", "c2"))
        assert (first.call_id, again.call_id) == ("c1", "c2")
        assert first.content == again.content == "echo: hi"
        assert world.tool.calls == [{"text": "hi"}]
        assert len(world.journal.entries("run-1")) == 1


def test_the_order_of_the_arguments_does_not_make_it_a_different_call() -> None:
    with made() as world:
        world.run(ToolCall("c1", "echo", {"text": "hi", "a": 1, "b": 2}))
        world.run(ToolCall("c2", "echo", {"b": 2, "a": 1, "text": "hi"}))
        assert len(world.tool.calls) == 1


def test_other_arguments_another_run_or_another_stage_is_a_new_call() -> None:
    with made() as world:
        world.run(say("hi"))
        world.run(say("ho"))
        world.run(say("hi"), run_id="run-2")
        world.run(say("hi"), stage="positioning")
        assert len(world.tool.calls) == 4


def test_the_journal_records_a_free_entry_for_the_tool_and_its_arguments() -> None:
    with made() as world:
        world.run(say("hi"))
        [entry] = world.journal.entries("run-1")
        assert (entry.stage, entry.attempt, entry.cost_micro_usd) == ("research", 1, 0)
        assert entry.key.model == "tool:echo"
        assert entry.response == '{"content": "echo: hi", "is_error": false}'


def test_a_failure_the_model_can_work_around_is_an_error_result_and_is_remembered() -> None:
    with made() as world:
        world.tool.fail = ApplicationError(code="PAGE_GONE", message="that page is gone")
        first = world.run(say())
        assert first == ToolResult("c1", "that page is gone", True)
        again = world.run(say("hi", "c2"))
        assert again == ToolResult("c2", "that page is gone", True)
        assert len(world.tool.calls) == 1


@pytest.mark.parametrize(
    "failure", [TransientStageError("slow"), CapacityExhaustedError("no credit")]
)
def test_a_failure_for_the_run_to_handle_goes_up_and_nothing_is_stored(
    failure: BaseException,
) -> None:
    with made() as world:
        world.tool.fail = failure
        with pytest.raises(type(failure)):
            world.run(say())
        assert world.journal.entries("run-1") == []
        world.tool.fail = None
        assert world.run(say()).content == "echo: hi"
        assert len(world.tool.calls) == 2


def test_a_long_result_is_cut_with_a_note_before_it_is_stored_or_shown() -> None:
    with made(ToolLoopLimits(result_characters=10)) as world:
        cut = "echo: xxxx\n[truncated: 26 more characters]"
        assert world.run(say("x" * 30)).content == cut
        [entry] = world.journal.entries("run-1")
        assert cut in entry.response.replace("\\n", "\n")
        assert world.run(say("x" * 30, "c2")).content == cut
        assert len(world.tool.calls) == 1


def test_a_result_exactly_at_the_limit_is_not_cut() -> None:
    with made(ToolLoopLimits(result_characters=10)) as world:
        assert world.run(say("xxxx")).content == "echo: xxxx"


def test_a_tool_that_does_not_answer_in_time_is_a_transient_failure_and_stores_nothing() -> None:
    with made(ToolLoopLimits(call_seconds=0.05)) as world:
        world.tool.block = threading.Event()
        try:
            with pytest.raises(TransientStageError, match="'echo' did not answer within 0.05 s"):
                world.run(say())
            assert world.journal.entries("run-1") == []
        finally:
            world.tool.block.set()


def test_the_runner_needs_a_worker() -> None:
    with pytest.raises(ValueError, match="at least one worker"):
        ToolRunner(ToolRegistry(()), InMemoryJournal(), ToolLoopLimits(), workers=0)


def test_a_closed_runner_takes_no_new_calls_and_closing_twice_is_harmless() -> None:
    world = World()
    world.runner.close()
    world.runner.close()
    with pytest.raises(RuntimeError):
        world.run(say())
    assert world.tool.calls == []
