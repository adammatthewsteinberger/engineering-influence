"""Settings loading, endpoint checks and the serve command."""

import argparse
import io
from collections.abc import Mapping
from contextlib import redirect_stderr
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.security.env_secret_provider import EnvSecretProvider
from engineering_influence.interactions.cli.serve_cli import ServeCli
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.runtime.api_runtime import ApiRuntime
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.cli_runtime import CliRuntime
from engineering_influence.runtime.endpoint_checks import EndpointChecks
from engineering_influence.runtime.environment_settings_loader import EnvironmentSettingsLoader
from engineering_influence.runtime.serve_starter import ServeStarter
from engineering_influence.runtime.worker_runtime import WorkerRuntime

DB = "postgresql+psycopg://svc:s3cretpw@db.internal:5432/ei"
MQ = "amqp://svc:rabbitpw@mq.internal:5672/"


class MappingSecrets(SecretProviderInterface):
    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = values

    def require(self, name: str) -> str:
        if not self._values.get(name, "").strip():
            raise ApplicationError(
                "SECRET_MISSING", f"required secret {name} is not configured", http_status=503
            )
        return self._values[name].strip()


def load(env: Mapping[str, str]) -> AppSettings:
    return EnvironmentSettingsLoader(MappingSecrets(env), env).load()


REQUIRED = {"EI_DATABASE_URL": DB, "EI_RABBITMQ_URL": MQ}


def test_the_required_settings_and_safe_defaults() -> None:
    settings = load(REQUIRED)

    assert settings == AppSettings(DB, MQ)
    assert (settings.host, settings.port, settings.log_level) == ("127.0.0.1", 8000, "INFO")
    assert settings.queue_name == "engineering-influence.jobs"


def test_every_setting_can_be_overridden() -> None:
    settings = load(
        {
            **REQUIRED,
            "EI_QUEUE_NAME": "jobs",
            "EI_LOG_LEVEL": "debug",
            "EI_HOST": "0.0.0.0",
            "EI_PORT": "9000",
            "EI_RATE_BURST": "5",
            "EI_RATE_PER_SECOND": "0.5",
        }
    )

    assert (settings.queue_name, settings.log_level, settings.host, settings.port) == (
        "jobs",
        "DEBUG",
        "0.0.0.0",
        9000,
    )
    assert (settings.rate_burst, settings.rate_per_second) == (5.0, 0.5)


@pytest.mark.parametrize("missing", ["EI_DATABASE_URL", "EI_RABBITMQ_URL"])
def test_a_missing_required_setting_stops_startup(missing: str) -> None:
    env = {key: value for key, value in REQUIRED.items() if key != missing}

    with pytest.raises(ApplicationError) as caught:
        load(env)

    assert caught.value.code == "SECRET_MISSING" and missing in caught.value.message


@pytest.mark.parametrize(
    ("name", "value", "fragment"),
    [
        ("EI_LOG_LEVEL", "LOUD", "EI_LOG_LEVEL"),
        ("EI_PORT", "0", "EI_PORT"),
        ("EI_PORT", "70000", "EI_PORT"),
        ("EI_PORT", "http", "EI_PORT"),
        ("EI_RATE_BURST", "lots", "EI_RATE_BURST must be a number"),
        ("EI_RATE_BURST", "0", "EI_RATE_BURST must be positive"),
        ("EI_RATE_PER_SECOND", "-1", "EI_RATE_PER_SECOND must be positive"),
    ],
)
def test_invalid_values_name_the_variable(name: str, value: str, fragment: str) -> None:
    with pytest.raises(ValueError, match=fragment):
        load({**REQUIRED, name: value})


def test_blank_optional_values_fall_back_to_the_default() -> None:
    assert load({**REQUIRED, "EI_HOST": "  "}).host == "127.0.0.1"


def test_the_real_environment_is_the_default_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", DB)
    monkeypatch.setenv("EI_RABBITMQ_URL", MQ)
    monkeypatch.setenv("EI_PORT", "8123")

    assert EnvironmentSettingsLoader(EnvSecretProvider()).load().port == 8123


def test_settings_never_print_their_credentials() -> None:
    text = repr(load(REQUIRED)) + str(load(REQUIRED))

    assert "s3cretpw" not in text and "rabbitpw" not in text and "svc" not in text


def test_an_endpoint_check_keeps_only_the_host_and_port() -> None:
    check = EndpointChecks.tcp("database", DB, 5432)

    assert check is not None
    assert check.name == "database"
    assert (check._host, check._port) == ("db.internal", 5432)


def test_an_endpoint_without_a_port_gets_the_default() -> None:
    check = EndpointChecks.tcp("mq", "amqp://guest:pw@broker/", 5672)

    assert check is not None and check._port == 5672


@pytest.mark.parametrize("url", ["sqlite://", "sqlite:///data/ei.db"])
def test_an_embedded_database_has_no_network_endpoint_to_check(url: str) -> None:
    assert EndpointChecks.tcp("db", url, 5432) is None


class Calls:
    def __init__(self) -> None:
        self.api: list[AppSettings] = []
        self.worker: list[AppSettings] = []


def cli(calls: Calls, values: Mapping[str, str]) -> ServeCli:
    return ServeCli(
        ServeStarter(
            MappingSecrets(values),
            run_api=lambda settings, _: calls.api.append(settings),
            run_worker=lambda settings, _: calls.worker.append(settings),
        )
    )


def run(
    serve: ServeCli, target: str, env: Mapping[str, str], monkeypatch: pytest.MonkeyPatch
) -> tuple[int, str]:
    for key in ("EI_DATABASE_URL", "EI_RABBITMQ_URL", "EI_PORT"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    buffer = io.StringIO()
    with redirect_stderr(buffer):
        status = serve.run(argparse.Namespace(target=target))
    return status, buffer.getvalue()


def test_serve_api_and_worker_run_their_own_process(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = Calls()

    assert run(cli(calls, REQUIRED), "api", REQUIRED, monkeypatch) == (0, "")
    assert run(cli(calls, REQUIRED), "worker", REQUIRED, monkeypatch) == (0, "")

    assert len(calls.api) == 1 and len(calls.worker) == 1


def test_a_configuration_error_exits_2_and_names_only_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = Calls()

    only_rabbit = {"EI_RABBITMQ_URL": MQ}

    status, stderr = run(cli(calls, only_rabbit), "api", only_rabbit, monkeypatch)

    assert status == 2
    assert stderr == "error: required secret EI_DATABASE_URL is not configured\n"
    assert calls.api == []


def test_a_value_error_also_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    status, stderr = run(
        cli(Calls(), REQUIRED), "worker", {**REQUIRED, "EI_PORT": "nope"}, monkeypatch
    )

    assert status == 2 and "EI_PORT" in stderr and "s3cretpw" not in stderr


def test_a_startup_failure_inside_the_runner_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(_: AppSettings, __: SecretProviderInterface) -> None:
        raise ApplicationError("SECRET_MISSING", "required secret EI_API_KEYS is not configured")

    serve = ServeCli(ServeStarter(MappingSecrets(REQUIRED), run_api=failing))

    status, stderr = run(serve, "api", REQUIRED, monkeypatch)

    assert status == 2 and "EI_API_KEYS" in stderr


def test_the_default_runners_start_the_real_runtimes(monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[str] = []

    class StartsApi(ApiRuntime):
        def run(self) -> None:
            started.append("api")

    class StartsWorker(WorkerRuntime):
        def run(self) -> None:
            started.append("worker")

    starter = ServeStarter(
        MappingSecrets(REQUIRED), api_runtime=StartsApi, worker_runtime=StartsWorker
    )
    serve = ServeCli(starter)

    run(serve, "api", REQUIRED, monkeypatch)
    run(serve, "worker", REQUIRED, monkeypatch)

    assert started == ["api", "worker"]


def test_without_a_factory_the_starter_builds_the_real_runtimes() -> None:
    settings = AppSettings("sqlite://", "amqp://guest:guest@localhost:1//")

    assert isinstance(ServeStarter._real_api(settings, MappingSecrets(REQUIRED)), ApiRuntime)
    assert isinstance(ServeStarter._real_worker(settings), WorkerRuntime)


def test_the_top_level_command_routes_serve(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("EI_DATABASE_URL", "EI_RABBITMQ_URL"):
        monkeypatch.delenv(key, raising=False)
    buffer = io.StringIO()

    with redirect_stderr(buffer):
        status = CliRuntime().build().run(["serve", "api"])

    assert status == 2 and "EI_DATABASE_URL" in buffer.getvalue()


def test_serve_only_accepts_known_targets() -> None:
    with pytest.raises(SystemExit):
        CliRuntime().build().run(["serve", "everything"])


def test_the_cli_builds_the_local_book_maker_from_the_environment_and_the_settings_it_is_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from engineering_influence.interfaces.local_book_creator_interface import (
        LocalBookCreatorInterface,
    )
    from engineering_influence.runtime.local_book_runtime import LocalBookRuntime

    profile = tmp_path / "author.toml"
    profile.write_text(
        'author = "A"\npublisher = "P"\nedition = "First Edition"\nauthor_bio = "B"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("EI_STAGE_EXECUTOR", "deterministic")
    monkeypatch.setenv("EI_AUTHOR_PROFILE", str(tmp_path / "not-there.toml"))
    creator = CliRuntime()._local_book_creator(
        tmp_path / "state", {"EI_AUTHOR_PROFILE": str(profile)}
    )
    try:
        assert isinstance(creator, LocalBookCreatorInterface)
    finally:
        creator.close()
    assert (tmp_path / "state" / LocalBookRuntime.DATABASE).is_file()


@pytest.mark.parametrize(
    ("value", "allowed"),
    [
        ("1", True),
        ("true", True),
        ("YES", True),
        (" Yes ", True),
        ("0", False),
        ("no", False),
        ("maybe", False),
        ("", False),
    ],
)
def test_the_mcp_server_may_spend_only_when_the_operator_says_so(value: str, allowed: bool) -> None:
    assert load({**REQUIRED, "EI_MCP_ALLOW_SPEND": value}).mcp_allow_spend is allowed
    assert load(REQUIRED).mcp_allow_spend is False


def test_serve_mcp_runs_the_mcp_runtime_with_the_settings_it_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started: list[AppSettings] = []

    class StartsMcp:
        def __init__(self, settings: AppSettings) -> None:
            self.settings = settings

        def run(self) -> None:
            started.append(self.settings)

    serve = ServeCli(ServeStarter(MappingSecrets(REQUIRED), mcp_runtime=StartsMcp))  # type: ignore[arg-type]
    assert run(serve, "mcp", {**REQUIRED, "EI_MCP_ALLOW_SPEND": "1"}, monkeypatch) == (0, "")
    assert [(item.database_url, item.mcp_allow_spend) for item in started] == [(DB, True)]


def test_without_a_factory_the_starter_builds_the_real_mcp_runtime() -> None:
    from engineering_influence.runtime.mcp_runtime import McpRuntime

    settings = AppSettings("sqlite://", "amqp://guest:guest@localhost:1//")
    assert isinstance(ServeStarter._real_mcp(settings), McpRuntime)


def test_serve_mcp_is_one_of_the_targets_and_a_configuration_error_exits_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = argparse.ArgumentParser()
    ServeCli(ServeStarter(MappingSecrets({}))).register(parser.add_subparsers(dest="command"))
    assert parser.parse_args(["serve", "mcp"]).target == "mcp"
    status, stderr = run(ServeCli(ServeStarter(MappingSecrets({}))), "mcp", {}, monkeypatch)
    assert status == 2 and "EI_DATABASE_URL" in stderr
