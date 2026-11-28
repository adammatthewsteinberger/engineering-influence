# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One model call, made at most once per request and never past the run's cap."""

import hashlib
import json
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.budget_exceeded_error import BudgetExceededError
from engineering_influence.errors.spend_consent_needed_error import SpendConsentNeededError
from engineering_influence.interfaces.journal_interface import JournalInterface
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.journal_entry import JournalEntry
from engineering_influence.models.journal_key import JournalKey
from engineering_influence.models.model_call_result import ModelCallResult
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.tool_call import ToolCall
from engineering_influence.services.interfaces.call_model_interface import CallModelInterface
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface


class CallModel(CallModelInterface):
    """The only way a stage reaches a model.

    1. A request already answered in this run and stage is **replayed** from the journal for
       nothing, so a resumed run never pays twice.
    2. Otherwise the worst-case cost is **reserved** from the guard before anything is sent; a
       call that does not fit raises BudgetExceededError having sent nothing.
    3. The call is made. If it raises, the reservation is released and nothing is journaled,
       because a transient or capacity failure made no charge.
    4. The answer is **journaled with its true cost before the reservation is settled**, so a
       crash between the two cannot lose the spend.

    Every billed call is journaled, because spend is the journal's total. A truncated or refused
    answer is journaled too, under a key that includes the outcome and the attempt: its cost
    counts, but a later lookup for a good answer to the same request never finds it, so a replay
    is always a complete answer and a retry is made, and paid for, afresh.

    **Tool turns are journaled whole.** A request that offers tools is keyed by the tools and the
    whole transcript so far, so each turn of a conversation has a key of its own and a replay is
    only ever of the same conversation. Its answer is stored as the text and the tool calls
    together. An ``end_turn`` and a ``tool_use`` are both complete answers and both replay. A
    request with no tools is keyed and stored exactly as before. A model that calls a tool when
    none was offered is billed and journaled like a cut-off answer (never replayed), and the call
    raises ``MODEL_RESPONSE_UNEXPECTED``: the adapters refuse this too, and this does not rely on it.
    """

    def __init__(self, model: ModelInterface, journal: JournalInterface) -> None:
        self._model = model
        self._journal = journal

    def call(
        self,
        guard: SpendGuardInterface,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ModelCallResult:
        """Replay the journaled answer, or reserve, call, journal and settle."""
        replayed = self.replay(run_id, stage, request)
        if replayed is not None:
            return replayed
        descriptor = self._model.describe()
        reserved = descriptor.worst_case_micro_usd(
            self._model.count_tokens(request), request.max_output_tokens
        )
        try:
            guard.reserve(reserved)
        except BudgetExceededError as error:
            raise SpendConsentNeededError(reserved) from error
        try:
            response = self._model.complete(request)
        except BaseException:
            guard.release(reserved)
            raise
        actual = descriptor.cost_micro_usd(response.usage)
        unoffered = bool(response.calls) and not request.tools
        replayable = response.stop_reason in ("end_turn", "tool_use") and not unoffered
        outcome = "" if replayable else f"|stop={response.stop_reason}|attempt={attempt}"
        key = self._key(descriptor.model, request, outcome)
        entry = JournalEntry(run_id, stage, attempt, key, self._encoded(request, response), actual)
        stored = self._journal.record(entry)
        if stored is not entry:
            # Another worker journaled this request first, so ours was paid for and not kept: count it.
            self._journal.spend(entry)
        guard.settle(reserved, actual)
        if unoffered:
            raise ApplicationError(
                code="MODEL_RESPONSE_UNEXPECTED",
                message="the model asked for tools that were not offered",
                http_status=502,
            )
        text, calls = self._decoded(request, stored.response)
        reason = ("tool_use" if calls else "end_turn") if replayable else response.stop_reason
        return ModelCallResult(text, reason, actual, False, calls)

    def replay(self, run_id: str, stage: str, request: ModelRequest) -> ModelCallResult | None:
        """The complete answer this run already has for the request, or None; costs nothing."""
        key = self._key(self._model.describe().model, request, "")
        recorded = self._journal.find(run_id, stage, key.digest())
        if recorded is None:
            return None
        text, calls = self._decoded(request, recorded.response)
        return ModelCallResult(text, "tool_use" if calls else "end_turn", 0, True, calls)

    @staticmethod
    def _encoded(request: ModelRequest, response: ModelResponse) -> str:
        if not request.tools:
            return response.text
        calls = [
            {"id": call.id, "name": call.name, "arguments": dict(call.arguments)}
            for call in response.calls
        ]
        return json.dumps(
            {"text": response.text, "calls": calls}, sort_keys=True, ensure_ascii=False
        )

    @staticmethod
    def _decoded(request: ModelRequest, stored: str) -> tuple[str, tuple[ToolCall, ...]]:
        if not request.tools:
            return stored, ()
        data = json.loads(stored)
        calls = tuple(ToolCall(c["id"], c["name"], c["arguments"]) for c in data["calls"])
        return str(data["text"]), calls

    @staticmethod
    def _key(model: str, request: ModelRequest, outcome: str) -> JournalKey:
        params = f"max_output_tokens={request.max_output_tokens}{outcome}"
        # JSON quotes and escapes every part, so no split of the texts can read as another.
        parts: list[Any] = [request.system, request.prompt]
        if request.tools:
            tools = [[t.name, t.description, t.json_schema()] for t in request.tools]
            turns = [
                [
                    turn.text,
                    [[c.name, c.arguments_json()] for c in turn.calls],
                    [
                        [r.call_id, r.content, r.is_error]
                        for r in (turn.result_for(c.id) for c in turn.calls)
                    ],
                ]
                for turn in request.transcript
            ]
            parts += [tools, turns]
        context = json.dumps(parts, sort_keys=True)
        return JournalKey(
            model=model,
            params_hash=hashlib.sha256(params.encode("utf-8")).hexdigest(),
            prompt_version=request.prompt_version,
            context_hash=hashlib.sha256(context.encode("utf-8")).hexdigest(),
        )
