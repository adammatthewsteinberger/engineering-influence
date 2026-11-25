"""The REST API contract: the OpenAPI document the stack really serves, and the shape of its errors."""

from collections.abc import Iterator, Mapping

import pytest
from fastapi.testclient import TestClient
from snapshot import Snapshot

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.runtime.api_runtime import ApiRuntime
from engineering_influence.runtime.app_settings import AppSettings

KEY = "a-valid-api-key-0123456789"  # gitleaks:allow
BROKER = "amqp://svc:rabbitpw@127.0.0.1:1/"


class Keys(SecretProviderInterface):
    def require(self, name: str) -> str:
        if name != "EI_API_KEYS":
            raise ApplicationError("SECRET_MISSING", name)
        return KEY


@pytest.fixture
def client(database_url: str) -> Iterator[TestClient]:
    """The app the stack serves, built by the same runtime, over a migrated database."""
    runtime = ApiRuntime(AppSettings(database_url, BROKER), Keys(), queue=InMemoryQueue())
    try:
        yield TestClient(runtime.build_app())
    finally:
        runtime.close()


def test_the_openapi_document_is_frozen(client: TestClient) -> None:
    Snapshot("rest_openapi").check(Snapshot.schema(client.app.openapi()))  # type: ignore[attr-defined]


def test_an_error_the_application_raises_has_a_code_a_message_and_whether_to_retry_and_a_malformed_request_has_detail(
    client: TestClient,
) -> None:
    # Two shapes, both frozen: what the application refuses is {code, message, retryable}; a request the framework
    # cannot read at all (a missing field, a wrong type) is FastAPI's {detail: [...]}, which the OpenAPI document
    # declares as HTTPValidationError.
    headers = {"Authorization": f"Bearer {KEY}"}
    answers: Mapping[str, object] = {
        "unknown_run": client.get("/v1/runs/nope", headers=headers),
        "unknown_artifact": client.get("/v1/runs/nope/artifacts/a.md", headers=headers),
        "no_key": client.get("/v1/runs/nope"),
        "bad_brief": client.post("/v1/runs", json={"kind": "nonfiction"}, headers=headers),
    }
    shape = {
        name: {"status": response.status_code, "keys": sorted(_keys(response.json()))}  # type: ignore[attr-defined]
        for name, response in answers.items()
    }
    Snapshot("rest_error_shapes").check(shape)


def _keys(body: object) -> list[str]:
    return list(body) if isinstance(body, dict) else ["<" + type(body).__name__ + ">"]
