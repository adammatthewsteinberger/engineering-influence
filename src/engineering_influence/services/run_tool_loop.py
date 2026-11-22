# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Asks a model, runs the tools it calls, and asks again, within limits."""

import dataclasses

from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_turn import ModelTurn
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.tool_call import ToolCall
from engineering_influence.models.tool_loop_limits import ToolLoopLimits
from engineering_influence.models.tool_loop_result import ToolLoopResult
from engineering_influence.models.tool_result import ToolResult
from engineering_influence.services.interfaces.ask_model_interface import AskModelInterface
from engineering_influence.services.interfaces.run_tool_loop_interface import (
    RunToolLoopInterface,
)
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface
from engineering_influence.services.interfaces.tool_runner_interface import ToolRunnerInterface


class RunToolLoop(RunToolLoopInterface):
    """Each turn is one ``AskModel`` call, so a cut-off or declined answer, a replay and the spend
    cap all work as they do for a stage that uses no tools. When the model answers with tool
    calls, each is run through the ``ToolRunner`` and the round is added to the transcript that the
    next request carries.

    - **A turn is journaled by what it was asked,** and the request includes the transcript so
      far, so a resumed run replays every finished turn and tool call for nothing and goes on from
      the first one it had not finished.
    - **Bounded.** After ``max_turns`` the loop stops with a blocking ``TOOL_LOOP_EXHAUSTED``
      issue. A call beyond ``max_tool_calls`` is not run; its result tells the model to answer with
      what it has. Neither the model nor a tool can make the loop run on.
    - **The request names the tools.** The runner is given the same names and runs nothing else,
      and the text the model has been shown so far, so a tool can check where an argument came from.
    - A request with no tools is one turn, so a stage can use this for every call.
    """

    def __init__(
        self, ask: AskModelInterface, runner: ToolRunnerInterface, limits: ToolLoopLimits
    ) -> None:
        self._ask = ask
        self._runner = runner
        self._limits = limits

    def run(
        self,
        guard: SpendGuardInterface,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ToolLoopResult:
        """The loop's outcome: the final text, or the best it got and the issues."""
        offered = tuple(tool.name for tool in request.tools)
        transcript: list[ModelTurn] = list(request.transcript)
        cost = model_calls = tool_calls = 0
        for turn in range(1, self._limits.max_turns + 1):
            answer = self._ask.ask(
                guard,
                run_id,
                stage,
                attempt,
                dataclasses.replace(request, transcript=tuple(transcript)),
            )
            cost += answer.cost_micro_usd
            model_calls += answer.calls
            if not answer.complete or not answer.tool_calls:
                return ToolLoopResult(
                    answer.text,
                    answer.complete,
                    answer.issues,
                    cost,
                    model_calls,
                    tool_calls,
                    turn,
                    tuple(transcript),
                )
            results: list[ToolResult] = []
            evidence = self._evidence(request, transcript)
            for call in answer.tool_calls:
                results.append(
                    self._result(run_id, stage, attempt, call, offered, evidence, tool_calls)
                )
                tool_calls += self._limits.room_for(tool_calls, 1)
            transcript.append(ModelTurn(answer.text, answer.tool_calls, tuple(results)))
        issue = QualityIssue(
            stage,
            "TOOL_LOOP_EXHAUSTED",
            f"the model was still asking for tools after {self._limits.max_turns} turns",
            blocking=True,
        )
        return ToolLoopResult(
            "",
            False,
            (issue,),
            cost,
            model_calls,
            tool_calls,
            self._limits.max_turns,
            tuple(transcript),
        )

    def _result(
        self,
        run_id: str,
        stage: str,
        attempt: int,
        call: ToolCall,
        offered: tuple[str, ...],
        evidence: str,
        made: int,
    ) -> ToolResult:
        if not self._limits.room_for(made, 1):
            return ToolResult(
                call.id, "no more tool calls are allowed; answer with what you have", True
            )
        return self._runner.run(run_id, stage, attempt, call, offered, evidence)

    @staticmethod
    def _evidence(request: ModelRequest, transcript: list[ModelTurn]) -> str:
        """What the model has legitimately been shown: the stage's prompt and every tool result."""
        shown = [request.prompt]
        shown += [result.content for turn in transcript for result in turn.results]
        return "\n".join(shown)
