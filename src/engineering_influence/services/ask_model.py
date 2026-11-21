# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Asks a model, and decides what to do when it cuts off or declines."""

import dataclasses

from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.model_answer import ModelAnswer
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.services.interfaces.ask_model_interface import AskModelInterface
from engineering_influence.services.interfaces.call_model_interface import CallModelInterface
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface


class AskModel(AskModelInterface):
    """A stage asks here, so that a cut-off or a refusal is handled the same way everywhere.

    - **Replay first.** Every output cap the escalation could reach is checked in the journal, for
      nothing, so a resumed run that already has an answer never pays for the attempts before it.
    - **Cut off** (the model hit its output cap): ask again with the cap doubled, up to the
      model's own limit. At the limit there is nothing more to try.
    - **Declined**: ask the identical request again, up to ``refusal_retries`` times. A refusal is
      the model's decision, so the request is never reworded, pressed or disguised; a retry only
      covers a refusal that was a fluke.
    - **Out of attempts**: the best text found (the cut-off text, or none if it only ever declined)
      comes back with a blocking QualityIssue for each defect, and the stage carries on. Running
      out of money is not handled here: the guard's BudgetExceededError, and a provider's
      capacity and transient errors, pass straight through to the run.

    Each live call gets its own journal attempt number, ``attempt * max_attempts + i``, so a stage's
    own retries and these attempts never share one, and every call's cost is counted.
    """

    REFUSAL_EXCERPT = 300

    def __init__(
        self,
        caller: CallModelInterface,
        model: ModelInterface,
        max_attempts: int = 4,
        refusal_retries: int = 1,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("at least one attempt is needed")
        if refusal_retries < 0:
            raise ValueError("refusal retries cannot be negative")
        self._caller = caller
        self._model = model
        self._max_attempts = max_attempts
        self._refusal_retries = refusal_retries

    def ask(
        self,
        guard: SpendGuardInterface,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ModelAnswer:
        """A complete answer, replayed or got live; otherwise the best text and the issues."""
        caps = self._caps(request)
        for cap in caps:
            replayed = self._caller.replay(run_id, stage, self._with_cap(request, cap))
            if replayed is not None:
                return ModelAnswer(replayed.text, True, (), 0, 0, True)
        index, refusals_left = 0, self._refusal_retries
        best: str | None = None
        last, declined = "", ""
        cost = calls = 0
        for tries in range(self._max_attempts):
            result = self._caller.call(
                guard,
                run_id,
                stage,
                attempt * self._max_attempts + tries,
                self._with_cap(request, caps[index]),
            )
            calls += 1
            cost += result.cost_micro_usd
            if result.stop_reason == "end_turn":
                return ModelAnswer(result.text, True, (), cost, calls, False)
            if result.stop_reason == "max_tokens":
                best, last = result.text, "max_tokens"
                if index == len(caps) - 1:
                    break
                index += 1
            else:
                last, declined = "refusal", result.text
                if refusals_left == 0:
                    break
                refusals_left -= 1
        issues = self._issues(stage, best, last, caps[index], calls, declined)
        return ModelAnswer(best or "", False, issues, cost, calls, False)

    def _caps(self, request: ModelRequest) -> list[int]:
        """The output caps to try, doubling from the request's up to the model's own limit."""
        limit = self._model.describe().max_output_tokens
        caps = [request.max_output_tokens]
        while caps[-1] < limit:
            caps.append(min(caps[-1] * 2, limit))
        return caps

    @staticmethod
    def _with_cap(request: ModelRequest, cap: int) -> ModelRequest:
        return dataclasses.replace(request, max_output_tokens=cap)

    def _issues(
        self, stage: str, best: str | None, last: str, cap: int, calls: int, declined: str
    ) -> tuple[QualityIssue, ...]:
        found: list[QualityIssue] = []
        if best is not None:
            found.append(
                QualityIssue(
                    stage,
                    "TRUNCATED",
                    f"the model stopped at its output limit ({cap} tokens) and the text ends "
                    f"part-way; {calls} attempt(s) made",
                    blocking=True,
                )
            )
        if last == "refusal":
            excerpt = " ".join(declined.split())[: self.REFUSAL_EXCERPT]
            found.append(
                QualityIssue(
                    stage,
                    "REFUSED",
                    f"the model declined to answer after {calls} attempt(s): {excerpt}",
                    blocking=True,
                )
            )
        return tuple(found)
