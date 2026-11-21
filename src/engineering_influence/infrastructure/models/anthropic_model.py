# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Claude over the Anthropic Messages API, called with plain httpx (ADR 0007)."""

from typing import Any, ClassVar

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_turn import ModelTurn
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.tool_call import ToolCall
from engineering_influence.models.tool_result import ToolResult


class AnthropicModel(ModelInterface):
    """Call one Claude model and sort every failure into retry, park or stop.

    The client is injected, so a test hands in one built on ``httpx.MockTransport``. The system
    prompt is sent as a cached block, so a stable prefix is billed at the cache-read rate on the
    calls after the first. The adapter never retries; the run decides, from the exception type.
    """

    API_VERSION = "2023-06-01"
    STOP_REASONS: ClassVar[dict[str, str]] = {
        "end_turn": "end_turn",
        "stop_sequence": "end_turn",
        "max_tokens": "max_tokens",
        "refusal": "refusal",
        "tool_use": "tool_use",
    }

    def __init__(
        self,
        client: httpx.Client,
        api_key: str,
        descriptor: ProviderDescriptor,
        base_url: str = "https://api.anthropic.com",
    ) -> None:
        if not api_key.strip():
            raise ValueError("an Anthropic model needs an API key")
        self._client = client
        self._api_key = api_key
        self._descriptor = descriptor
        self._base_url = base_url.rstrip("/")
        self._blocked = ModelAvailability.AVAILABLE

    def describe(self) -> ProviderDescriptor:
        """The configured model's identity, limits and prices."""
        return self._descriptor

    def availability(self) -> ModelAvailability:
        """What the last call learned: blocked on credit or credentials until a call succeeds.

        Anthropic offers no free probe, so a model nobody has called yet reads as available.
        """
        return self._blocked

    def count_tokens(self, request: ModelRequest) -> int:
        """Ask the token-counting endpoint how many input tokens the request will use."""
        data = self._post("/v1/messages/count_tokens", self._body(request, with_output_cap=False))
        try:
            return int(data["input_tokens"])
        except (KeyError, TypeError, ValueError) as error:
            raise self._unexpected("token count") from error

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Send the request and map the reply onto the vendor-neutral response."""
        data = self._post("/v1/messages", self._body(request, with_output_cap=True))
        try:
            text = "".join(
                block["text"] for block in data["content"] if block.get("type") == "text"
            )
            calls = tuple(
                ToolCall(str(block["id"]), str(block["name"]), block["input"])
                for block in data["content"]
                if block.get("type") == "tool_use"
            )
            if calls and not request.tools:
                raise self._unexpected("tool call that was not offered")
            usage = data["usage"]
            reason = self.STOP_REASONS.get(data["stop_reason"])
            if reason is None:
                raise self._unexpected(f"stop reason {data['stop_reason']!r}")
            return ModelResponse(
                text=text,
                usage=ModelUsage(
                    input_tokens=int(usage["input_tokens"]),
                    output_tokens=int(usage["output_tokens"]),
                    cache_read_tokens=int(usage.get("cache_read_input_tokens") or 0),
                    cache_write_tokens=int(usage.get("cache_creation_input_tokens") or 0),
                ),
                model_snapshot=str(data["model"]),
                stop_reason=reason,
                calls=calls,
            )
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            raise self._unexpected("response") from error

    def _body(self, request: ModelRequest, with_output_cap: bool) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self._descriptor.model,
            "messages": self._messages(request),
        }
        if request.tools:
            body["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.json_schema(),
                }
                for tool in request.tools
            ]
        if request.system.strip():
            body["system"] = [
                {
                    "type": "text",
                    "text": request.system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        if with_output_cap:
            body["max_tokens"] = request.max_output_tokens
        return body

    @classmethod
    def _messages(cls, request: ModelRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{"role": "user", "content": request.prompt}]
        for turn in request.transcript:
            messages.append({"role": "assistant", "content": cls._assistant_blocks(turn)})
            messages.append(
                {
                    "role": "user",
                    "content": [cls._result_block(turn.result_for(call.id)) for call in turn.calls],
                }
            )
        return messages

    @staticmethod
    def _assistant_blocks(turn: ModelTurn) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        if turn.text.strip():
            blocks.append({"type": "text", "text": turn.text})
        blocks.extend(
            {"type": "tool_use", "id": call.id, "name": call.name, "input": dict(call.arguments)}
            for call in turn.calls
        )
        return blocks

    @staticmethod
    def _result_block(result: ToolResult) -> dict[str, Any]:
        block: dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": result.call_id,
            "content": result.content,
        }
        if result.is_error:
            block["is_error"] = True
        return block

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }
        try:
            response = self._client.post(self._base_url + path, json=body, headers=headers)
        except httpx.TransportError as error:
            raise TransientStageError(
                f"Anthropic could not be reached: {type(error).__name__}"
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
        kind, message = self._error_detail(response)
        if status in (401, 403):
            self._blocked = ModelAvailability.AUTHENTICATION_FAILED
            return CapacityExhaustedError(f"Anthropic refused the API key ({status}): {message}")
        if status == 402 or (status == 400 and "credit balance" in message.lower()):
            self._blocked = ModelAvailability.CREDITS_EXHAUSTED
            return CapacityExhaustedError(f"Anthropic credit is exhausted: {message}")
        if status == 429 or status >= 500:
            return TransientStageError(f"Anthropic answered {status} ({kind}): {message}")
        return ApplicationError(
            code="MODEL_REJECTED",
            message=f"Anthropic rejected the request ({status}, {kind}): {message}",
            http_status=502,
        )

    @staticmethod
    def _error_detail(response: httpx.Response) -> tuple[str, str]:
        try:
            error = response.json()["error"]
            return str(error["type"]), str(error["message"])[:300]
        except (KeyError, TypeError, ValueError):
            return "unknown", response.text[:300]

    @staticmethod
    def _unexpected(what: str) -> ApplicationError:
        return ApplicationError(
            code="MODEL_RESPONSE_UNEXPECTED",
            message=f"Anthropic sent a {what} this adapter does not understand",
            http_status=502,
        )
