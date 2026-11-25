# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs one tool call safely, once per run, and remembers what it said."""

import hashlib
import json
from collections.abc import Collection, Sequence
from concurrent.futures import ThreadPoolExecutor

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.journal_interface import JournalInterface
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.interfaces.tool_registry_interface import ToolRegistryInterface
from engineering_influence.models.journal_entry import JournalEntry
from engineering_influence.models.journal_key import JournalKey
from engineering_influence.models.model_turn import ModelTurn
from engineering_influence.models.tool_call import ToolCall
from engineering_influence.models.tool_loop_limits import ToolLoopLimits
from engineering_influence.models.tool_result import ToolResult
from engineering_influence.services.interfaces.tool_runner_interface import ToolRunnerInterface


class ToolRunner(ToolRunnerInterface):
    """The one place a tool is run.

    - **Only offered tools exist.** A call to a name the stage was not given, or one nobody
      registered, gets an error result the model can read; nothing runs.
    - **Arguments are checked first** against the tool's schema, and a bad call gets an error
      result saying what is wrong. A tool can then refuse a call by what the model has been shown
      (``ToolInterface.refuses``), which is how ``fetch_url`` keeps a hostile page from steering
      the model to an address that carries data out. What counts as shown is the prompt and the
      part of each earlier successful result that its own tool vouches for, never an error or
      anything the model typed. Refusals are ours: they are not journaled and not wrapped.
    - **A call is made once.** Its result is journaled by tool and arguments, so a resumed or
      retried run, or a model that asks the same thing twice, gets the stored result and the web
      is not asked again. A tool failure the model can work around (``ApplicationError``) is stored
      as an error result; a transient or capacity failure is not stored and goes up to the run.
    - **A result is cut** to the limit, with a note of how much, before it is stored or shown.
    - **Whatever a tool says is untrusted.** Its text, and the text of an error it raises, is
      wrapped in an ``<untrusted name="tool:...">`` block that it cannot close early. The
      runner's own refusals (no such tool, bad arguments) are ours and are not wrapped.
    - **A call has a time limit.** A tool that has not answered in ``call_seconds`` raises
      ``TransientStageError``. Its thread cannot be killed, so a tool should also bound itself;
      the pool is small, so a tool that never returns fills it and later calls time out.
    """

    VERSION = "tool-v1"

    def __init__(
        self,
        registry: ToolRegistryInterface,
        journal: JournalInterface,
        limits: ToolLoopLimits,
        workers: int = 4,
    ) -> None:
        if workers < 1:
            raise ValueError("at least one worker is needed")
        self._registry = registry
        self._journal = journal
        self._limits = limits
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="tool")

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
        """The result of the call, replayed from the journal if this run already made it."""
        tool = self._registry.lookup(call.name) if call.name in offered else None
        if tool is None:
            return ToolResult(call.id, f"no tool named {call.name!r} is available here", True)
        problem = tool.definition().check(call.arguments)
        if problem:
            return ToolResult(call.id, f"invalid arguments: {problem}", True)
        reason = tool.refuses(call.arguments, self._evidence(prompt, transcript))
        if reason:
            return ToolResult(call.id, reason, True)
        key = self._key(call, tool)
        recorded = self._journal.find(run_id, stage, key.digest())
        if recorded is None:
            made = (
                self._invoke(tool, call)
                .capped(self._limits.result_characters)
                .untrusted(f"tool:{call.name}")
            )
            entry = JournalEntry(run_id, stage, attempt, key, self._encoded(made), 0)
            recorded = self._journal.record(entry)
        return self._decoded(call, recorded.response)

    def _evidence(self, prompt: str, transcript: Sequence[ModelTurn]) -> str:
        """What the model has legitimately been shown: the prompt, and what each tool vouches for.

        Only a successful result counts, and only the part its own tool names. The runner's
        refusals and a tool's errors are left out because they can echo what the model typed,
        which would let a call launder an address into the evidence by naming it. A call to a tool
        that is not registered counts for nothing.
        """
        shown = [prompt]
        for turn in transcript:
            for call in turn.calls:
                result = turn.result_for(call.id)
                tool = self._registry.lookup(call.name)
                if tool is not None and not result.is_error:
                    shown.append(tool.shown(result.content))
        return "\n".join(shown)

    def close(self) -> None:
        """Stop accepting calls and let the threads that run tools finish."""
        self._pool.shutdown(wait=False, cancel_futures=True)

    def _invoke(self, tool: ToolInterface, call: ToolCall) -> ToolResult:
        future = self._pool.submit(tool.invoke, call.arguments)
        try:
            return ToolResult(call.id, future.result(timeout=self._limits.call_seconds))
        except TimeoutError as error:
            raise TransientStageError(
                f"tool {call.name!r} did not answer within {self._limits.call_seconds:g} seconds"
            ) from error
        except ApplicationError as error:
            return ToolResult(call.id, error.message, True)

    def _key(self, call: ToolCall, tool: ToolInterface) -> JournalKey:
        revision = tool.revision()
        return JournalKey(
            model=f"tool:{call.name}",
            params_hash=hashlib.sha256(call.arguments_json().encode("utf-8")).hexdigest(),
            prompt_version=f"{self.VERSION}:{revision}" if revision else self.VERSION,
            context_hash=hashlib.sha256(b"tool").hexdigest(),
        )

    @staticmethod
    def _encoded(result: ToolResult) -> str:
        return json.dumps({"content": result.content, "is_error": result.is_error})

    @staticmethod
    def _decoded(call: ToolCall, stored: str) -> ToolResult:
        data = json.loads(stored)
        return ToolResult(call.id, data["content"], data["is_error"])
