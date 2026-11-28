# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Agent Client Protocol over JSON-RPC: a session is a book run, and a prompt is its brief."""

from __future__ import annotations

import json
import sys
import threading
import uuid
from typing import TYPE_CHECKING, Any, ClassVar

from engineering_influence import __version__
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.acp.interfaces.application_interface import (
    AcpApplicationInterface,
)
from engineering_influence.interfaces.acp_session_store_interface import AcpSessionStoreInterface
from engineering_influence.models.acp_session import AcpSession
from engineering_influence.models.run_status import RunStatus
from engineering_influence.services.interfaces.brief_reader_interface import BriefReaderInterface
from engineering_influence.services.interfaces.cancel_run_interface import CancelRunInterface
from engineering_influence.services.interfaces.create_run_interface import CreateRunInterface
from engineering_influence.services.interfaces.resolve_spend_consent_interface import (
    ResolveSpendConsentInterface,
)
from engineering_influence.services.interfaces.run_progress_interface import RunProgressInterface

if TYPE_CHECKING:
    from typing import TextIO

    from engineering_influence.models.book_run import BookRun


class AcpApplication(AcpApplicationInterface):
    """Protocol version 1, as the stable specification describes it.

    ``initialize`` agrees the version (this agent speaks 1 and says so). ``session/new`` makes a session; a session
    is one book run, started by the first ``session/prompt``, whose text is the brief written as TOML. The prompt is
    answered with ``end_turn`` once the run is saved and its first stage queued, because the stages are done by the
    worker, not here. ``session/cancel`` stops the run. Progress is reported as ``session/update`` notifications.

    Sessions are stored beside the runs, so ``session/load`` re-attaches one from any process, and a run outlives its
    session: a new session can find it with ``ei run status``. A run that would spend past its cap asks the client
    through ``session/request_permission``, and the answer decides the run. MCP servers are not connected:
    ``session/new`` refuses a non-empty ``mcpServers`` list, since a server the client names would run commands this
    agent has not locked.
    """

    PROTOCOL_VERSION: ClassVar[int] = 1
    SUPPORTED: ClassVar[frozenset[str]] = frozenset(
        {"initialize", "session/new", "session/load", "session/prompt", "session/cancel"}
    )
    # JSON-RPC 2.0 error codes, by the code a refusal carries.
    JSONRPC_CODES: ClassVar[dict[str, int]] = {
        "ACP_PARSE": -32700,
        "ACP_INVALID_REQUEST": -32600,
        "ACP_METHOD_NOT_FOUND": -32601,
        "ACP_INVALID_PARAMS": -32602,
        "BRIEF_INVALID": -32602,
        "RUN_KIND_UNSUPPORTED": -32602,
    }
    INTERNAL: ClassVar[int] = -32603
    # A finished run is reported once and then no longer followed; a parked run can still be resumed.
    FINISHED: ClassVar[frozenset[RunStatus]] = frozenset(
        {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}
    )

    def __init__(
        self,
        creator: CreateRunInterface,
        canceller: CancelRunInterface,
        briefs: BriefReaderInterface,
        progress: RunProgressInterface,
        resolver: ResolveSpendConsentInterface,
        sessions: AcpSessionStoreInterface,
    ) -> None:
        self._creator = creator
        self._canceller = canceller
        self._briefs = briefs
        self._progress = progress
        self._resolver = resolver
        self._store = sessions
        self._cwds: dict[str, str] = {}
        # Permission requests sent and not yet answered: request id -> (session id, run id).
        self._open_requests: dict[str, tuple[str, str]] = {}
        # Guards the sessions and the reported states: the reader thread and the follower both use them.
        self._lock = threading.Lock()
        self._sessions: dict[str, str | None] = {}
        # For each session whose run is still followed: the run's id and the (status, stage) last reported.
        self._reported: dict[str, tuple[str, tuple[str, str]]] = {}

    def handle(self, message: Any) -> list[dict[str, Any]]:
        """The messages to send back for one incoming message; a notification gets none unless it fails."""
        request_id = message.get("id") if isinstance(message, dict) else None
        try:
            with self._lock:
                return self._dispatch(message)
        except ApplicationError as error:
            if request_id is None:
                return []
            code = self.JSONRPC_CODES.get(error.code, self.INTERNAL)
            return [self._error(request_id, code, error.message)]
        except Exception as error:  # noqa: BLE001 - one failed call must not end the stdio server
            # Only the class name goes to stderr: a message can carry a connection string.
            print(f"error: {type(error).__name__} while handling a message", file=sys.stderr)
            if request_id is None:
                return []
            return [self._error(request_id, self.INTERNAL, "internal error")]

    def serve(self, reader: TextIO, writer: TextIO, poll_seconds: float = 1.0) -> None:
        """Read messages until the input ends, writing each reply as one line, flushed at once.

        A follower thread writes the progress notices every ``poll_seconds`` while the input is open. Each
        line is written under one lock, so a notice never lands in the middle of a reply.
        """
        write_lock = threading.Lock()
        stop = threading.Event()

        def send(messages: list[dict[str, Any]]) -> None:
            if not messages:
                return
            with write_lock:
                writer.writelines(json.dumps(item, ensure_ascii=False) + "\n" for item in messages)
                writer.flush()

        def follow() -> None:
            # The first pass runs before the stop flag is checked, so a run that changed is reported even
            # when the input ends at once.
            while True:
                try:
                    send(self.follow_messages())
                except Exception as error:  # noqa: BLE001 - following must not end the reader's loop
                    print(f"error: {type(error).__name__} while following a run", file=sys.stderr)
                if stop.wait(poll_seconds):
                    return

        follower = threading.Thread(target=follow, daemon=True)
        follower.start()
        try:
            for line in reader:
                text = line.strip()
                if not text:
                    continue
                try:
                    message = json.loads(text)
                except json.JSONDecodeError:
                    messages = [
                        self._error(None, self.JSONRPC_CODES["ACP_PARSE"], "the line is not JSON")
                    ]
                else:
                    messages = self.handle(message)
                send(messages)
        finally:
            stop.set()
            follower.join()

    def follow_messages(self) -> list[dict[str, Any]]:
        """The messages the follower writes now: a notice for each change in a followed run, and a permission
        request when a run starts waiting for consent.

        A finished run is reported once and then dropped. A run is asked about once per state it enters, so a
        request is not repeated while the run keeps waiting.
        """
        messages: list[dict[str, Any]] = []
        with self._lock:
            for session_id, (run_id, reported) in list(self._reported.items()):
                run = self._progress.current(run_id)
                if run is None:
                    continue
                state = (run.status.value, run.stage)
                if state == reported:
                    continue
                messages.append(self._update(session_id, self._progress_text(run)))
                consent = run.consent
                if run.status is RunStatus.AWAITING_CONSENT and consent is not None:
                    messages.append(
                        self._consent_request(session_id, run_id, consent.requested_micro_usd)
                    )
                if run.status in self.FINISHED:
                    del self._reported[session_id]
                else:
                    self._reported[session_id] = (run_id, state)
        return messages

    def _consent_request(self, session_id: str, run_id: str, requested: int) -> dict[str, Any]:
        """Ask the client whether the run may spend more; the answer returns as a response with this id."""
        request_id = f"consent-{uuid.uuid4().hex}"
        self._open_requests[request_id] = (session_id, run_id)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "session/request_permission",
            "params": {
                "sessionId": session_id,
                "toolCall": {
                    "toolCallId": f"spend-{run_id}-{requested}",
                    "title": f"Spend {requested} micro-USD more on run {run_id}",
                    "status": "pending",
                },
                "options": [
                    {
                        "optionId": "grant",
                        "name": f"Allow {requested} micro-USD more",
                        "kind": "allow_once",
                    },
                    {"optionId": "deny", "name": "Refuse; the run parks", "kind": "reject_once"},
                ],
            },
        }

    def _answer(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        """The client's answer to a permission request: grant or deny the run, or keep it waiting."""
        request_id = message["id"]
        opened = self._open_requests.get(request_id) if isinstance(request_id, str) else None
        if opened is None:
            return []
        run_id = opened[1]
        result = message.get("result")
        outcome = result.get("outcome") if isinstance(result, dict) else None
        if not isinstance(outcome, dict) or outcome.get("outcome") != "selected":
            return []  # the request was cancelled or not answered: the run keeps waiting
        choice = outcome.get("optionId")
        if choice not in ("grant", "deny"):
            return []
        del self._open_requests[request_id]
        try:
            if choice == "grant":
                self._resolver.grant(run_id)
            else:
                self._resolver.deny(run_id)
        except ApplicationError as error:
            # The run moved on before the answer arrived; there is nothing left to decide.
            print(f"error: {error.code} while answering a consent request", file=sys.stderr)
        return []

    @staticmethod
    def _progress_text(run: BookRun) -> str:
        return f"run {run.run_id} is {run.status.value} at stage {run.stage!r}"

    def _dispatch(self, message: Any) -> list[dict[str, Any]]:
        if (
            isinstance(message, dict)
            and message.get("jsonrpc") == "2.0"
            and "method" not in message
            and "id" in message
        ):
            return self._answer(message)
        if (
            not isinstance(message, dict)
            or message.get("jsonrpc") != "2.0"
            or not isinstance(message.get("method"), str)
        ):
            raise self._refusal(
                "ACP_INVALID_REQUEST", "a message is a JSON-RPC 2.0 object with a method"
            )
        method = message["method"]
        request_id = message.get("id")
        params = message.get("params", {})
        if not isinstance(params, dict):
            raise self._refusal("ACP_INVALID_PARAMS", f"{method} takes an object of parameters")
        if method not in self.SUPPORTED:
            raise self._refusal("ACP_METHOD_NOT_FOUND", f"this agent does not implement {method}")
        if method == "initialize":
            return self._reply(request_id, self._initialize())
        if method == "session/new":
            return self._reply(request_id, self._new_session(params))
        if method == "session/load":
            return self._load(request_id, params)
        if method == "session/prompt":
            return self._prompt(request_id, params)
        self._cancel(params)
        return []

    def _initialize(self) -> dict[str, Any]:
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "agentCapabilities": {"loadSession": True},
            "agentInfo": {"name": "engineering-influence", "version": __version__},
            "authMethods": [],
        }

    def _new_session(self, params: dict[str, Any]) -> dict[str, Any]:
        cwd = params.get("cwd")
        if not isinstance(cwd, str) or not cwd.startswith("/"):
            raise self._refusal("ACP_INVALID_PARAMS", "cwd is an absolute path")
        if params.get("mcpServers", []) != []:
            raise self._refusal("ACP_INVALID_PARAMS", "this agent does not connect MCP servers yet")
        session_id = f"sess_{uuid.uuid4().hex}"
        self._sessions[session_id] = None
        self._cwds[session_id] = cwd
        self._store.save(AcpSession(session_id, cwd, None))
        return {"sessionId": session_id}

    def _prompt(self, request_id: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
        session_id = self._session(params)
        if self._sessions[session_id] is not None:
            raise self._refusal(
                "ACP_INVALID_PARAMS",
                f"this session already has run {self._sessions[session_id]}",
            )
        text = self._text(params.get("prompt"))
        run = self._creator.create(self._briefs.read_text(text, "the prompt"))
        self._sessions[session_id] = run.run_id
        self._store.save(AcpSession(session_id, self._cwds[session_id], run.run_id))
        self._reported[session_id] = (run.run_id, (run.status.value, run.stage))
        notice = self._update(
            session_id,
            f"run {run.run_id} is {run.status.value} at stage {run.stage!r}; its first stage is queued",
        )
        return [notice, *self._reply(request_id, {"stopReason": "end_turn"})]

    def _load(self, request_id: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Re-attach a stored session and replay where its run stands; the reply has no result."""
        session_id = params.get("sessionId")
        cwd = params.get("cwd")
        if not isinstance(session_id, str) or not isinstance(cwd, str) or not cwd.startswith("/"):
            raise self._refusal(
                "ACP_INVALID_PARAMS", "sessionId names a session; cwd is an absolute path"
            )
        stored = self._store.get(session_id)
        if stored is None:
            raise self._refusal(
                "ACP_INVALID_PARAMS", "sessionId names a session this agent started"
            )
        self._sessions[session_id] = stored.run_id
        self._cwds[session_id] = stored.cwd
        messages: list[dict[str, Any]] = []
        if stored.run_id is not None:
            run = self._progress.current(stored.run_id)
            if run is not None:
                messages.append(self._update(session_id, self._progress_text(run)))
                if run.status not in self.FINISHED:
                    self._reported[session_id] = (stored.run_id, (run.status.value, run.stage))
        return [*messages, {"jsonrpc": "2.0", "id": request_id, "result": None}]

    def _cancel(self, params: dict[str, Any]) -> None:
        session_id = self._session(params)
        run_id = self._sessions[session_id]
        if run_id is None:
            return
        self._canceller.cancel(run_id)

    def _session(self, params: dict[str, Any]) -> str:
        session_id = params.get("sessionId")
        if not isinstance(session_id, str) or session_id not in self._sessions:
            raise self._refusal(
                "ACP_INVALID_PARAMS", "sessionId names a session this agent started"
            )
        return session_id

    def _text(self, prompt: Any) -> str:
        if not isinstance(prompt, list) or not prompt:
            raise self._refusal(
                "ACP_INVALID_PARAMS", "prompt is a non-empty list of content blocks"
            )
        parts = []
        for block in prompt:
            if (
                not isinstance(block, dict)
                or block.get("type") != "text"
                or not isinstance(block.get("text"), str)
            ):
                raise self._refusal("ACP_INVALID_PARAMS", "only text content blocks are supported")
            parts.append(block["text"])
        return "\n".join(parts)

    @staticmethod
    def _refusal(code: str, message: str) -> ApplicationError:
        return ApplicationError(code=code, message=message, http_status=400)

    @staticmethod
    def _reply(request_id: Any, result: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"jsonrpc": "2.0", "id": request_id, "result": result}]

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    @staticmethod
    def _update(session_id: str, text: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "method": "session/update",
            "params": {
                "sessionId": session_id,
                "update": {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": text},
                },
            },
        }
