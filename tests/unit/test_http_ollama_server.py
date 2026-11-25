"""HttpOllamaServer: what Ollama says about its models and how one was loaded, and what a server that is not Ollama says."""

from collections.abc import Callable
from typing import Any

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.models.http_ollama_server import HttpOllamaServer
from engineering_influence.interfaces.ollama_server_interface import OllamaServerInterface


def server(handler: Callable[[httpx.Request], httpx.Response]) -> HttpOllamaServer:
    return HttpOllamaServer(
        httpx.Client(transport=httpx.MockTransport(handler)), "http://ollama.test/"
    )


def answering(tags: Any = None, ps: Any = None, status: int = 200) -> HttpOllamaServer:
    def handler(request: httpx.Request) -> httpx.Response:
        body = tags if request.url.path == "/api/tags" else ps
        return httpx.Response(status, json=body)

    return server(handler)


def test_it_is_an_ollama_server_port() -> None:
    assert isinstance(answering(), OllamaServerInterface)


def test_the_pulled_models_are_listed_by_name_from_the_trimmed_address() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200, json={"models": [{"name": "gpt-oss:20b"}, {"name": "qwen3:14b"}]}
        )

    assert server(handler).models() == ("gpt-oss:20b", "qwen3:14b")
    assert seen == ["http://ollama.test/api/tags"]


def test_an_entry_with_no_name_is_skipped() -> None:
    assert answering({"models": [{"size": 1}, {"name": "a"}]}).models() == ("a",)


def test_an_empty_list_is_an_ollama_with_nothing_pulled() -> None:
    assert answering({"models": []}).models() == ()


def test_no_more_than_five_hundred_models_are_read() -> None:
    many = {"models": [{"name": f"m{n}"} for n in range(HttpOllamaServer.MAX_MODELS + 5)]}
    assert len(answering(many).models() or ()) == 500


@pytest.mark.parametrize(
    "body",
    [{"nothing": 1}, {"models": "x"}, {"models": 5}, {"models": [1, 2]}, [1], "text", None],
)
def test_an_answer_that_is_not_a_model_list_means_it_is_not_ollama(body: Any) -> None:
    assert answering(body).models() is None


def test_an_error_status_means_it_is_not_ollama() -> None:
    assert answering({"models": []}, status=404).models() is None


def test_a_reply_that_is_not_json_means_it_is_not_ollama() -> None:
    assert server(lambda request: httpx.Response(200, text="<html>")).models() is None


@pytest.mark.parametrize("error", [httpx.ConnectError("refused"), httpx.ReadTimeout("slow")])
def test_a_server_that_does_not_answer_is_unreachable(error: httpx.HTTPError) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    with pytest.raises(ApplicationError) as caught:
        server(handler).models()
    assert (caught.value.code, caught.value.http_status) == ("LOCAL_SERVER_UNREACHABLE", 503)
    assert caught.value.message == "nothing answers at http://ollama.test"


def loaded(*entries: dict[str, Any]) -> HttpOllamaServer:
    return answering(ps={"models": list(entries)})


def test_the_loaded_context_is_read_for_the_model_asked_about() -> None:
    value = loaded(
        {"name": "other", "context_length": 1}, {"name": "gpt-oss:20b", "context_length": 32768}
    )
    assert value.loaded_context("gpt-oss:20b") == 32768


def test_a_model_loaded_under_its_latest_tag_is_found() -> None:
    assert (
        loaded({"name": "mymodel:latest", "context_length": 8192}).loaded_context("mymodel") == 8192
    )


def test_a_model_that_is_not_loaded_has_no_context() -> None:
    assert loaded({"name": "other", "context_length": 1}).loaded_context("gpt-oss:20b") is None
    assert loaded().loaded_context("gpt-oss:20b") is None


@pytest.mark.parametrize("length", [None, "32768", 3.5, True])
def test_a_context_that_is_not_a_whole_number_is_not_read(length: Any) -> None:
    assert loaded({"name": "m", "context_length": length}).loaded_context("m") is None


def test_a_missing_context_field_is_not_read() -> None:
    assert loaded({"name": "m"}).loaded_context("m") is None


def test_a_server_that_cannot_say_what_is_loaded_gives_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    assert server(handler).loaded_context("m") is None
    assert answering(ps={"models": []}, status=500).loaded_context("m") is None
