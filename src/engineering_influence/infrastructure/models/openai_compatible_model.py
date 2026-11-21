# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Any server that speaks the OpenAI Chat Completions shape, called with plain httpx (ADR 0007)."""

import json
from typing import Any, ClassVar

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.tool_call import ToolCall


class OpenAICompatibleModel(ModelInterface):
    """Call OpenAI, or a local server such as Ollama, vLLM or llama.cpp, and sort every failure.

    The client is injected. ``api_key`` may be blank for a local server, and then no
    ``Authorization`` header is sent. ``output_cap_field`` names the body field that caps the
    reply: servers expect ``max_tokens``, while current OpenAI models want
    ``max_completion_tokens``. The adapter never retries; the run decides from the exception type.
    """

    FINISH_REASONS: ClassVar[dict[str, str]] = {
        "stop": "end_turn",
        "length": "max_tokens",
        "content_filter": "refusal",
        "tool_calls": "tool_use",
    }
    MESSAGE_OVERHEAD_TOKENS = 8

    def __init__(
        self,
        client: httpx.Client,
        api_key: str,
        descriptor: ProviderDescriptor,
        base_url: str = "https://api.openai.com",
        output_cap_field: str = "max_tokens",
    ) -> None:
        self._client = client
        self._api_key = api_key.strip()
        self._descriptor = descriptor
        self._base_url = base_url.rstrip("/")
        self._output_cap_field = output_cap_field
        self._blocked = ModelAvailability.AVAILABLE

    def describe(self) -> ProviderDescriptor:
        """The configured model's identity, limits and prices."""
        return self._descriptor

    def availability(self) -> ModelAvailability:
        """What the last call learned: blocked on credit or credentials until a call succeeds."""
        return self._blocked

    def count_tokens(self, request: ModelRequest) -> int:
        """An upper bound on the input tokens, since the shape has no counting endpoint.

        Every token decodes to at least one byte, so the UTF-8 length of the text can never be
        lower than the token count; a fixed overhead per message covers the chat template. A
        reservation made from this over-reserves, which the settlement after the call corrects
        from the real ``prompt_tokens`` the server reports.
        """
        messages = self._messages(request)
        text_bytes = sum(len((message["content"] or "").encode("utf-8")) for message in messages)
        calls = [message["tool_calls"] for message in messages if "tool_calls" in message]
        tools = self._tools(request)
        extra_bytes = (
            len(json.dumps([calls, tools], ensure_ascii=False).encode("utf-8"))
            if calls or tools
            else 0
        )
        return text_bytes + extra_bytes + self.MESSAGE_OVERHEAD_TOKENS * len(messages)

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Send the request and map the reply onto the vendor-neutral response."""
        body: dict[str, Any] = {
            "model": self._descriptor.model,
            "messages": self._messages(request),
            self._output_cap_field: request.max_output_tokens,
        }
        if request.tools:
            body["tools"] = self._tools(request)
        data = self._post("/v1/chat/completions", body)
        try:
            choice = data["choices"][0]
            message = choice["message"]
            reason = self.FINISH_REASONS.get(choice["finish_reason"])
            if message.get("refusal"):
                reason = "refusal"
            calls = self._calls(message)
            if calls and not request.tools:
                raise self._unexpected("tool call that was not offered")
            if calls and reason == "end_turn":
                reason = "tool_use"  # some local servers say "stop" even when they call a tool
            if reason is None:
                raise self._unexpected(f"finish reason {choice['finish_reason']!r}")
            usage = data["usage"]
            cached = int((usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
            return ModelResponse(
                text=message.get("content") or "",
                usage=ModelUsage(
                    input_tokens=int(usage["prompt_tokens"]) - cached,
                    output_tokens=int(usage["completion_tokens"]),
                    cache_read_tokens=cached,
                ),
                model_snapshot=str(data["model"]),
                stop_reason=reason,
                calls=calls,
            )
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as error:
            raise self._unexpected("response") from error

    @staticmethod
    def _messages(request: ModelRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{"role": "user", "content": request.prompt}]
        if request.system.strip():
            messages.insert(0, {"role": "system", "content": request.system})
        for turn in request.transcript:
            messages.append(
                {
                    "role": "assistant",
                    "content": turn.text if turn.text.strip() else None,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {"name": call.name, "arguments": call.arguments_json()},
                        }
                        for call in turn.calls
                    ],
                }
            )
            for call in turn.calls:
                result = turn.result_for(call.id)
                text = f"Error: {result.content}" if result.is_error else result.content
                messages.append({"role": "tool", "tool_call_id": call.id, "content": text})
        return messages

    @staticmethod
    def _tools(request: ModelRequest) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.json_schema(),
                },
            }
            for tool in request.tools
        ]

    @staticmethod
    def _calls(message: dict[str, Any]) -> tuple[ToolCall, ...]:
        calls: list[ToolCall] = []
        for entry in message.get("tool_calls") or []:
            function = entry["function"]
            arguments = function["arguments"]
            if isinstance(arguments, str):
                arguments = json.loads(arguments or "{}")
            calls.append(ToolCall(str(entry["id"]), str(function["name"]), arguments))
        return tuple(calls)

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        headers = {"content-type": "application/json"}
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"
        try:
            response = self._client.post(self._base_url + path, json=body, headers=headers)
        except httpx.TransportError as error:
            raise TransientStageError(
                f"the model server could not be reached: {type(error).__name__}"
            ) from error
        if response.status_code == 200:
            self._blocked = ModelAvailability.AVAILABLE
            try:
                data = response.json()
            except ValueError as error:
                raise self._unexpected("body") from error
            if not isinstance(data, dict):
                raise self._unexpected("body")
            return data
        raise self._failure(response)

    def _failure(self, response: httpx.Response) -> Exception:
        status = response.status_code
        code, message = self._error_detail(response)
        if status in (401, 403):
            self._blocked = ModelAvailability.AUTHENTICATION_FAILED
            return CapacityExhaustedError(
                f"the model server refused the API key ({status}): {message}"
            )
        if status == 402 or code == "insufficient_quota":
            self._blocked = ModelAvailability.CREDITS_EXHAUSTED
            return CapacityExhaustedError(f"the model account is out of credit: {message}")
        if status in (408, 429) or status >= 500:
            return TransientStageError(f"the model server answered {status} ({code}): {message}")
        return ApplicationError(
            code="MODEL_REJECTED",
            message=f"the model server rejected the request ({status}, {code}): {message}",
            http_status=502,
        )

    @staticmethod
    def _error_detail(response: httpx.Response) -> tuple[str, str]:
        try:
            error = response.json()["error"]
            code = error.get("code") or error.get("type") or "unknown"
            return str(code), str(error["message"])[:300]
        except (KeyError, TypeError, ValueError, AttributeError):
            return "unknown", response.text[:300]

    @staticmethod
    def _unexpected(what: str) -> ApplicationError:
        return ApplicationError(
            code="MODEL_RESPONSE_UNEXPECTED",
            message=f"the model server sent a {what} this adapter does not understand",
            http_status=502,
        )
