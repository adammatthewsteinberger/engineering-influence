"""Every way into the stack holds a run to the operator's spend ceilings: REST, MCP, the CLI and ACP."""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.spend_limits import SpendLimits
from engineering_influence.models.spend_request import SpendRequest
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository
from engineering_influence.runtime.api_runtime import ApiRuntime
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.cli_runtime import CliRuntime
from engineering_influence.runtime.mcp_runtime import McpRuntime
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes

BROKER = "amqp://svc:rabbitpw@127.0.0.1:1/"
KEY = "a-valid-api-key-0123456789"  # gitleaks:allow
LIMITS = SpendLimits(per_run=2_000_000, outstanding=3_000_000)


class Keys(SecretProviderInterface):
    def require(self, name: str) -> str:
        if name != "EI_API_KEYS":
            raise ApplicationError("SECRET_MISSING", name)
        return KEY


def body(budget: int) -> dict[str, Any]:
    return {"schema_version": 1, "kind": "nonfiction", "idea": "bees", "budget_micro_usd": budget}


def waiting(repo: SqlModelRunRepository, run_id: str, cap: int, asked: int) -> None:
    brief = BookBrief(BookKind.NONFICTION, "bees", cap)
    run = BookRun(run_id, brief, NonfictionRecipes().plan(), Budget(cap=cap)).start()
    repo.save(run.await_consent(SpendRequest(asked, run.stage)))


def test_the_settings_carry_the_ceilings_the_environment_sets() -> None:
    from engineering_influence.runtime.environment_settings_loader import EnvironmentSettingsLoader

    environ = {
        "EI_DATABASE_URL": "sqlite://",
        "EI_RABBITMQ_URL": BROKER,
        "EI_MAX_RUN_BUDGET_MICRO_USD": "2000000",
        "EI_MAX_OUTSTANDING_BUDGET_MICRO_USD": "3000000",
    }

    class Environ(SecretProviderInterface):
        def require(self, name: str) -> str:
            return environ[name]

    assert EnvironmentSettingsLoader(Environ(), environ).load().spend_limits == LIMITS
    with pytest.raises(ValueError, match="EI_MAX_RUN_BUDGET_MICRO_USD"):
        EnvironmentSettingsLoader(
            Environ(), {**environ, "EI_MAX_RUN_BUDGET_MICRO_USD": "no"}
        ).load()


def test_the_rest_api_refuses_a_run_and_a_grant_that_break_a_ceiling(database_url: str) -> None:
    repo = SqlModelRunRepository(database_url)
    waiting(repo, "w", 2_000_000, 1_000_000)
    api = ApiRuntime(
        AppSettings(database_url, BROKER, spend_limits=LIMITS), Keys(), queue=InMemoryQueue()
    )
    try:
        client = TestClient(api.build_app())
        headers = {"Authorization": f"Bearer {KEY}"}
        over = client.post("/v1/runs", json=body(2_000_001), headers=headers)
        assert over.status_code == 422 and over.json()["code"] == "BUDGET_ABOVE_LIMIT"
        assert client.post("/v1/runs", json=body(1_000_000), headers=headers).status_code == 201
        crowded = client.post("/v1/runs", json=body(1_000_000), headers=headers)
        assert (
            crowded.status_code == 422 and crowded.json()["code"] == "OUTSTANDING_BUDGET_EXCEEDED"
        )
        granted = client.post("/v1/runs/w/grant", json={"micro_usd": None}, headers=headers)
        assert granted.status_code == 422 and granted.json()["code"] == "BUDGET_ABOVE_LIMIT"
    finally:
        api.close()
        repo.close()


def test_mcp_holds_the_same_ceilings(database_url: str) -> None:
    mcp = McpRuntime(
        AppSettings(database_url, BROKER, spend_limits=LIMITS, mcp_allow_spend=True),
        queue=InMemoryQueue(),
    )
    repo = SqlModelRunRepository(database_url)
    waiting(repo, "w", 2_000_000, 1_500_000)
    try:
        tools = {name: tool.fn for name, tool in mcp.build_server()._tool_manager._tools.items()}
        with pytest.raises(ApplicationError) as over:
            tools["create_run"](body(2_000_001))
        assert over.value.code == "BUDGET_ABOVE_LIMIT"
        with pytest.raises(ApplicationError) as raised:
            tools["grant_run"]("w")
        assert raised.value.code == "BUDGET_ABOVE_LIMIT"
        assert tools["create_run"](body(1_000_000))["status"] == "pending"
    finally:
        mcp.close()
        repo.close()


def write_brief(tmp_path: Path, budget: int) -> Path:
    path = tmp_path / "brief.toml"
    path.write_text(
        f'kind = "nonfiction"\nidea = "bees"\nbudget_micro_usd = {budget}\n', encoding="utf-8"
    )
    return path


def test_the_cli_refuses_a_run_over_the_ceiling_and_starts_one_under_it(
    database_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    monkeypatch.setenv("EI_MAX_RUN_BUDGET_MICRO_USD", "2000000")
    queue = InMemoryQueue()
    runtime = CliRuntime(queue=queue)
    assert runtime.build().run(["run", "create", str(write_brief(tmp_path, 2_000_001))]) != 0
    assert "at most 2000000 micro-USD" in capsys.readouterr().err and queue.jobs == []
    assert runtime.build().run(["run", "create", str(write_brief(tmp_path, 2_000_000))]) == 0
    assert len(queue.jobs) == 1


def test_the_cli_refuses_a_grant_over_the_ceiling(
    database_url: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    monkeypatch.setenv("EI_MAX_OUTSTANDING_BUDGET_MICRO_USD", "2500000")
    repo = SqlModelRunRepository(database_url)
    waiting(repo, "w", 2_000_000, 1_000_000)
    queue = InMemoryQueue()
    assert CliRuntime(queue=queue).build().run(["run", "grant", "w"]) != 0
    assert "hold at most 2500000" in capsys.readouterr().err and queue.jobs == []
    stored = repo.get("w")
    assert stored is not None and stored.status is RunStatus.AWAITING_CONSENT
    repo.close()


def test_acp_is_built_with_the_ceiling_too(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    monkeypatch.setenv("EI_MAX_RUN_BUDGET_MICRO_USD", "2000000")
    application: Any = CliRuntime(queue=InMemoryQueue())._acp_application()
    creator = application._creator
    brief = BookBrief(BookKind.NONFICTION, "bees", 2_000_001)
    with pytest.raises(ApplicationError) as error:
        creator.create(brief)
    assert error.value.code == "BUDGET_ABOVE_LIMIT"
    repo = SqlModelRunRepository(database_url)
    waiting(repo, "w", 2_000_000, 1_000_000)
    with pytest.raises(ApplicationError) as grant:
        application._resolver.grant("w")
    assert grant.value.code == "BUDGET_ABOVE_LIMIT"
    repo.close()


def test_without_ceilings_nothing_is_refused(
    database_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    monkeypatch.delenv("EI_MAX_RUN_BUDGET_MICRO_USD", raising=False)
    monkeypatch.delenv("EI_MAX_OUTSTANDING_BUDGET_MICRO_USD", raising=False)
    assert (
        CliRuntime(queue=InMemoryQueue())
        .build()
        .run(["run", "create", str(write_brief(tmp_path, 900_000_000))])
        == 0
    )
