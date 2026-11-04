"""Settings loading, endpoint checks and the serve command."""

import argparse
import io
from collections.abc import Mapping
from contextlib import redirect_stderr

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.security.env_secret_provider import EnvSecretProvider
from engineering_influence.interaction.cli.main import CliApplication
from engineering_influence.interaction.cli.serve_cli import ServeCli
from engineering_influence.interfaces.secret_provider_port import SecretProviderPort
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.endpoint_checks import EndpointChecks
from engineering_influence.runtime.environment_settings_loader import EnvironmentSettingsLoader

DB = "postgresql+psycopg://svc:s3cretpw@db.internal:5432/ei"
MQ = "amqp://svc:rabbitpw@mq.internal:5672/"


class MappingSecrets(SecretProviderPort):
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
        MappingSecrets(values),
        run_api=lambda settings, _: calls.api.append(settings),
        run_worker=lambda settings, _: calls.worker.append(settings),
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
    def failing(_: AppSettings, __: SecretProviderPort) -> None:
        raise ApplicationError("SECRET_MISSING", "required secret EI_API_KEYS is not configured")

    serve = ServeCli(MappingSecrets(REQUIRED), run_api=failing)

    status, stderr = run(serve, "api", REQUIRED, monkeypatch)

    assert status == 2 and "EI_API_KEYS" in stderr


def test_the_default_runners_start_the_real_runtimes(monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[str] = []
    monkeypatch.setattr(
        "engineering_influence.runtime.api_runtime.ApiRuntime.run",
        lambda self: started.append("api"),
    )
    monkeypatch.setattr(
        "engineering_influence.runtime.worker_runtime.WorkerRuntime.run",
        lambda self: started.append("worker"),
    )
    serve = ServeCli(MappingSecrets(REQUIRED))

    run(serve, "api", REQUIRED, monkeypatch)
    run(serve, "worker", REQUIRED, monkeypatch)

    assert started == ["api", "worker"]


def test_the_top_level_command_routes_serve(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("EI_DATABASE_URL", "EI_RABBITMQ_URL"):
        monkeypatch.delenv(key, raising=False)
    buffer = io.StringIO()

    with redirect_stderr(buffer):
        status = CliApplication().run(["serve", "api"])

    assert status == 2 and "EI_DATABASE_URL" in buffer.getvalue()


def test_serve_only_accepts_known_targets() -> None:
    with pytest.raises(SystemExit):
        CliApplication().run(["serve", "everything"])
