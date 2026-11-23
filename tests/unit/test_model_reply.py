"""Reading a model's reply: a JSON object is returned, and anything else is the same error, naming the server."""

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.models.model_reply import ModelReply


def reply(content: bytes) -> httpx.Response:
    return httpx.Response(200, content=content)


def test_a_json_object_is_the_body() -> None:
    assert ModelReply.body(reply(b'{"content": []}'), "Anthropic") == {"content": []}


@pytest.mark.parametrize("content", [b"[1, 2]", b'"text"', b"42", b"null", b"not json"])
def test_anything_but_a_json_object_is_an_unexpected_reply_naming_the_server(
    content: bytes,
) -> None:
    with pytest.raises(ApplicationError) as caught:
        ModelReply.body(reply(content), "the model server")
    assert caught.value.code == "MODEL_RESPONSE_UNEXPECTED"
    assert caught.value.http_status == 502
    assert caught.value.message == "the model server sent a body this adapter does not understand"


def test_the_unexpected_error_names_what_was_not_understood() -> None:
    error = ModelReply.unexpected("Anthropic", "body")
    assert error.code == "MODEL_RESPONSE_UNEXPECTED"
    assert error.message == "Anthropic sent a body this adapter does not understand"
