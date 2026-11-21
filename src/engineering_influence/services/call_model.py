# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One model call, made at most once per request and never past the run's cap."""

import hashlib

from engineering_influence.interfaces.journal_interface import JournalInterface
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.journal_entry import JournalEntry
from engineering_influence.models.journal_key import JournalKey
from engineering_influence.models.model_call_result import ModelCallResult
from engineering_influence.models.model_request import ModelRequest
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
        descriptor = self._model.describe()
        key = self._key(descriptor.model, request, "")
        recorded = self._journal.find(run_id, stage, key.digest())
        if recorded is not None:
            return ModelCallResult(recorded.response, "end_turn", 0, True)
        reserved = descriptor.worst_case_micro_usd(
            self._model.count_tokens(request), request.max_output_tokens
        )
        guard.reserve(reserved)
        try:
            response = self._model.complete(request)
        except BaseException:
            guard.release(reserved)
            raise
        actual = descriptor.cost_micro_usd(response.usage)
        if response.stop_reason != "end_turn":
            key = self._key(
                descriptor.model, request, f"|stop={response.stop_reason}|attempt={attempt}"
            )
        entry = JournalEntry(run_id, stage, attempt, key, response.text, actual)
        stored = self._journal.record(entry)
        guard.settle(reserved, actual)
        return ModelCallResult(stored.response, response.stop_reason, actual, False)

    @staticmethod
    def _key(model: str, request: ModelRequest, outcome: str) -> JournalKey:
        params = f"max_output_tokens={request.max_output_tokens}{outcome}"
        context = request.system + "\x1e" + request.prompt
        return JournalKey(
            model=model,
            params_hash=hashlib.sha256(params.encode("utf-8")).hexdigest(),
            prompt_version=request.prompt_version,
            context_hash=hashlib.sha256(context.encode("utf-8")).hexdigest(),
        )
