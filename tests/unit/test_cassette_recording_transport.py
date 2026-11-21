# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""CassetteRecordingTransport: the caller gets the real answer, the cassette a masked copy."""

import gzip
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.cassettes.cassette_recording_transport import (
    CassetteRecordingTransport,
)
from engineering_influence.infrastructure.cassettes.cassette_redactor import CassetteRedactor
from engineering_influence.infrastructure.cassettes.json_cassette_store import JsonCassetteStore
from engineering_influence.interfaces.cassette_recorder_interface import (
    CassetteRecorderInterface,
)

KEY = "sk-test-SECRETSECRET"
URL = "http://provider.test"


class Inner(httpx.BaseTransport):
    """A provider that answers from a function and notes when it was closed."""

    def __init__(self, answer: Any) -> None:
        self._answer = answer
        self.closed = False

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._answer(request)

    def close(self) -> None:
        self.closed = True


def recorder(
    tmp_path: Path, answer: Any
) -> tuple[CassetteRecordingTransport, httpx.Client, JsonCassetteStore, Inner]:
    store = JsonCassetteStore(tmp_path / "cassettes", CassetteRedactor([KEY]))
    inner = Inner(answer)
    transport = CassetteRecordingTransport(inner, CassetteRedactor([KEY]), store)
    return transport, httpx.Client(transport=transport), store, inner


def ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"text": "A harbour at dawn."})


def test_it_is_a_cassette_recorder(tmp_path: Path) -> None:
    transport, _, _, _ = recorder(tmp_path, ok)
    assert isinstance(transport, CassetteRecorderInterface)


def test_the_caller_gets_the_real_answer_and_the_cassette_a_masked_copy(tmp_path: Path) -> None:
    def echo(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": f"invalid x-api-key {KEY}"})

    transport, client, store, _ = recorder(tmp_path, echo)
    reply = client.post(
        f"{URL}/v1/messages?key={KEY}",
        json={"prompt": f"my key is {KEY}"},
        headers={"x-api-key": KEY, "authorization": f"Bearer {KEY}"},
    )
    assert reply.json() == {"error": f"invalid x-api-key {KEY}"}
    saved = transport.finish("echo-key", "anthropic", "synthetic")
    only = saved.interactions[0]
    assert only.method == "POST"
    assert only.path == "/v1/messages?key=[REDACTED]"
    assert only.request_body == {"prompt": "my key is [REDACTED]"}
    assert (only.status, only.response_body) == (401, {"error": "invalid x-api-key [REDACTED]"})
    on_disk = (tmp_path / "cassettes" / "echo-key.json").read_text(encoding="utf-8")
    assert KEY not in on_disk
    assert "x-api-key" not in on_disk.replace("invalid x-api-key", "")
    assert store.load("echo-key") == saved


def test_exchanges_are_kept_in_the_order_they_happened(tmp_path: Path) -> None:
    transport, client, _, _ = recorder(tmp_path, ok)
    client.post(f"{URL}/v1/a", json={"n": 1})
    client.get(f"{URL}/v1/b")
    saved = transport.finish("two-calls", "test")
    assert [(item.method, item.path, item.request_body) for item in saved.interactions] == [
        ("POST", "/v1/a", {"n": 1}),
        ("GET", "/v1/b", None),
    ]
    assert saved.note == ""


def test_an_empty_answer_is_recorded_as_none(tmp_path: Path) -> None:
    transport, client, _, _ = recorder(tmp_path, lambda request: httpx.Response(204))
    client.delete(f"{URL}/v1/x")
    assert transport.finish("empty", "test").interactions[0].response_body is None


def test_a_request_that_is_not_json_cannot_be_recorded(tmp_path: Path) -> None:
    _, client, _, _ = recorder(tmp_path, ok)
    with pytest.raises(ApplicationError) as error:
        client.post(f"{URL}/v1/a", content=b"plain text")
    assert error.value.code == "CASSETTE_UNRECORDABLE"
    assert "the request was not JSON" in error.value.message


def test_an_answer_that_is_not_json_cannot_be_recorded(tmp_path: Path) -> None:
    _, client, _, _ = recorder(tmp_path, lambda request: httpx.Response(200, text="<html>"))
    with pytest.raises(ApplicationError) as error:
        client.get(f"{URL}/v1/a")
    assert error.value.code == "CASSETTE_UNRECORDABLE"
    assert "the response was not JSON" in error.value.message


def test_finishing_with_nothing_recorded_is_refused(tmp_path: Path) -> None:
    transport, _, _, _ = recorder(tmp_path, ok)
    with pytest.raises(ApplicationError) as error:
        transport.finish("nothing", "test")
    assert (error.value.code, error.value.message) == (
        "CASSETTE_INVALID",
        "nothing was recorded, so there is no cassette to save",
    )


def test_finishing_under_a_bad_name_is_refused_and_writes_nothing(tmp_path: Path) -> None:
    transport, client, _, _ = recorder(tmp_path, ok)
    client.get(f"{URL}/v1/a")
    with pytest.raises(ApplicationError) as error:
        transport.finish("Bad Name", "test")
    assert error.value.code == "CASSETTE_INVALID"
    assert "not a cassette name" in error.value.message
    assert not (tmp_path / "cassettes").exists()


def test_closing_the_recorder_closes_the_transport_underneath(tmp_path: Path) -> None:
    _, client, _, inner = recorder(tmp_path, ok)
    client.close()
    assert inner.closed


@contextmanager
def gzip_server() -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["content-length"]))
            body = gzip.compress(json.dumps({"text": "caf\u00e9"}).encode())
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-encoding", "gzip")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_over_a_real_socket_the_caller_still_reads_a_compressed_answer_the_recorder_read(
    tmp_path: Path,
) -> None:
    store = JsonCassetteStore(tmp_path, CassetteRedactor([KEY]))
    with gzip_server() as url:
        transport = CassetteRecordingTransport(
            httpx.HTTPTransport(), CassetteRedactor([KEY]), store
        )
        with httpx.Client(transport=transport) as client:
            reply = client.post(f"{url}/v1/messages", json={"prompt": "one"})
    assert reply.json() == {"text": "caf\u00e9"}
    saved = transport.finish("real-socket", "test")
    assert saved.interactions[0].response_body == {"text": "caf\u00e9"}
