"""The local model doctor: the server, the model, one tiny answer and the context, in the order a person fixes them."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.interfaces.ollama_server_interface import OllamaServerInterface
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.services.local_default_model import LocalDefaultModel
from engineering_influence.services.local_model_doctor import LocalModelDoctor

FREE = LocalDefaultModel({})


class Server(OllamaServerInterface):
    def __init__(
        self,
        models: tuple[str, ...] | None = ("gpt-oss:20b",),
        context: int | None = 131_072,
        down: bool = False,
    ) -> None:
        self._models, self._context, self._down = models, context, down
        self.asked: list[str] = []

    def models(self) -> tuple[str, ...] | None:
        if self._down:
            raise ApplicationError(code="LOCAL_SERVER_UNREACHABLE", message="nothing answers")
        return self._models

    def loaded_context(self, model: str) -> int | None:
        self.asked.append(model)
        return self._context


class Model(ModelInterface):
    def __init__(
        self, text: str = "ready", stop: str = "end_turn", fail: Exception | None = None
    ) -> None:
        self._text, self._stop, self._fail = text, stop, fail
        self.requests: list[ModelRequest] = []

    def describe(self) -> ProviderDescriptor:
        return FREE.descriptor()

    def availability(self) -> ModelAvailability:
        return ModelAvailability.AVAILABLE

    def count_tokens(self, request: ModelRequest) -> int:
        return 1

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if self._fail is not None:
            raise self._fail
        return ModelResponse(self._text, ModelUsage(5, 3), "snap", self._stop)


def lines(model: Model | None = None, server: Server | None = None) -> list[str]:
    return [
        item.line() for item in LocalModelDoctor(FREE, model or Model(), server or Server()).check()
    ]


def test_a_ready_setup_passes_all_four_checks() -> None:
    assert lines() == [
        "ok   local: server: Ollama answers at http://127.0.0.1:11434",
        "ok   local: model: gpt-oss:20b is pulled",
        "ok   local: answers: gpt-oss:20b replied in 3 tokens",
        "ok   local: context: 131072 tokens, at least the 131072 a prompt is assembled to fit",
    ]


def test_the_question_asked_is_one_tiny_fixed_request() -> None:
    model = Model()
    LocalModelDoctor(FREE, model, Server()).check()
    (request,) = model.requests
    assert (request.system, request.prompt, request.max_output_tokens, request.prompt_version) == (
        "",
        "Reply with the single word: ready.",
        256,
        "doctor-local@1",
    )


def test_a_server_that_does_not_answer_stops_everything_else() -> None:
    model = Model()
    found = [item.line() for item in LocalModelDoctor(FREE, model, Server(down=True)).check()]
    assert found == [
        (
            "FAIL local: server: nothing answers at http://127.0.0.1:11434; install Ollama from "
            "https://ollama.com and start it, or set EI_LOCAL_URL to the server you run"
        )
    ]
    assert model.requests == []


def test_a_model_that_is_not_pulled_names_the_command_and_asks_nothing() -> None:
    model = Model()
    found = [
        item.line()
        for item in LocalModelDoctor(FREE, model, Server(models=("llama3.1:8b",))).check()
    ]
    assert found[1] == "FAIL local: model: gpt-oss:20b is not pulled; run: ollama pull gpt-oss:20b"
    assert len(found) == 2 and model.requests == []


def test_the_latest_tag_counts_as_the_model() -> None:
    free = LocalDefaultModel({"EI_LOCAL_MODEL": "mymodel"})
    found = LocalModelDoctor(free, Model(), Server(models=("mymodel:latest",))).check()
    assert [item.check for item in found] == ["server", "model", "answers", "context"]
    assert all(item.passed for item in found)


def test_a_server_that_is_not_ollama_is_checked_by_its_answer_only() -> None:
    server = Server(models=None)
    found = [item.line() for item in LocalModelDoctor(FREE, Model(), server).check()]
    assert found == [
        (
            "ok   local: server: something answers at http://127.0.0.1:11434, but it is not Ollama, "
            "so the model and context checks are skipped"
        ),
        "ok   local: answers: gpt-oss:20b replied in 3 tokens",
    ]
    assert server.asked == []


@pytest.mark.parametrize(
    "error",
    [
        TransientStageError("timed out"),
        CapacityExhaustedError("quota"),
        ApplicationError(code="X", message="refused"),
    ],
)
def test_a_completion_that_fails_is_reported_and_stops_the_context_check(error: Exception) -> None:
    server = Server()
    found = [item.line() for item in LocalModelDoctor(FREE, Model(fail=error), server).check()]
    assert found[-1].startswith("FAIL local: answers: could not complete: ")
    assert len(found) == 3 and server.asked == []


def test_what_an_error_says_is_flattened_and_cut() -> None:
    error = TransientStageError("line one\nline" + chr(0x7) + "two " + "x" * 400)
    last = lines(Model(fail=error))[-1]
    assert "\n" not in last and chr(0x7) not in last
    assert last == "FAIL local: answers: could not complete: line one line two " + "x" * (
        200 - len("line one line two ")
    )


@pytest.mark.parametrize("text", ["", "   \n"])
def test_an_empty_reply_is_a_failure_that_says_why(text: str) -> None:
    server = Server()
    found = lines(Model(text=text, stop="max_tokens"), server)
    assert found[-1] == (
        "FAIL local: answers: gpt-oss:20b returned nothing (it stopped for max_tokens); "
        "its reasoning may have used the whole cap"
    )
    assert server.asked == []


def test_a_context_below_what_a_prompt_assumes_is_a_failure_with_the_fix() -> None:
    found = lines(server=Server(context=4096))
    assert found[-1] == (
        "FAIL local: context: Ollama loaded gpt-oss:20b with a context of 4096, below the 131072 a prompt is "
        "assembled to fit, and it would cut a prompt short; start Ollama with OLLAMA_CONTEXT_LENGTH=131072"
    )


def test_a_context_one_below_fails_and_one_above_passes() -> None:
    assert lines(server=Server(context=131_071))[-1].startswith("FAIL local: context")
    assert lines(server=Server(context=131_073))[-1].startswith("ok   local: context")


def test_a_context_the_server_does_not_report_cannot_be_checked() -> None:
    assert lines(server=Server(context=None))[-1] == (
        "FAIL local: context: Ollama did not say what context gpt-oss:20b was loaded with, so it cannot be checked"
    )


def test_the_context_is_asked_for_the_model_in_use() -> None:
    server = Server()
    LocalModelDoctor(FREE, Model(), server).check()
    assert server.asked == ["gpt-oss:20b"]
