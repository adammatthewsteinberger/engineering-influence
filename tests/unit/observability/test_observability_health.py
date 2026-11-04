"""Dependency checks and the readiness service."""

import socket
from collections.abc import Iterator

import pytest

from engineering_influence.contracts.health_status import HealthStatus
from engineering_influence.infrastructure.observability.tcp_health_check import TcpHealthCheck
from engineering_influence.infrastructure.observability.toolchain_health_check import (
    ToolchainHealthCheck,
)
from engineering_influence.interfaces.health_check_port import HealthCheckPort
from engineering_influence.services.readiness_probe import ReadinessProbe


@pytest.fixture
def listening_port() -> Iterator[int]:
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    yield int(server.getsockname()[1])
    server.close()


def closed_port() -> int:
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    port = int(holder.getsockname()[1])
    holder.close()
    return port


def test_an_open_port_is_healthy(listening_port: int) -> None:
    status = TcpHealthCheck("rabbitmq", "127.0.0.1", listening_port).check()

    assert status == HealthStatus(name="rabbitmq", healthy=True)


def test_a_closed_port_is_unhealthy_without_revealing_the_address() -> None:
    port = closed_port()
    check = TcpHealthCheck("postgres", "127.0.0.1", port)

    status = check.check()

    assert check.name == "postgres"
    assert not status.healthy
    assert status.detail == "ConnectionRefusedError"
    assert "127.0.0.1" not in str(status) and str(port) not in str(status)


def test_a_host_that_does_not_resolve_is_unhealthy() -> None:
    status = TcpHealthCheck("db", "no-such-host.invalid", 5432, timeout_seconds=1.0).check()

    assert not status.healthy
    assert status.detail == "gaierror"


def test_the_toolchain_is_healthy_when_every_executable_exists() -> None:
    check = ToolchainHealthCheck(locator=lambda name: f"/usr/bin/{name}")

    assert check.check().healthy
    assert check.name == "tex-toolchain"


def test_the_toolchain_names_what_is_missing() -> None:
    check = ToolchainHealthCheck(
        ("lualatex", "latexmk", "epubcheck"),
        locator=lambda name: None if name != "latexmk" else "/usr/bin/latexmk",
        name="build-tools",
    )

    status = check.check()

    assert not status.healthy
    assert status.detail == "missing: lualatex, epubcheck"
    assert check.name == "build-tools"


def test_the_default_locator_uses_the_real_path() -> None:
    assert not ToolchainHealthCheck(("definitely-not-installed-xyz",)).check().healthy


class Fixed(HealthCheckPort):
    """A check with a canned result."""

    def __init__(self, name: str, healthy: bool) -> None:
        self._name = name
        self._healthy = healthy

    @property
    def name(self) -> str:
        return self._name

    def check(self) -> HealthStatus:
        return HealthStatus(
            name=self._name, healthy=self._healthy, detail=None if self._healthy else "down"
        )


class Exploding(HealthCheckPort):
    """A check that raises, as a buggy third-party client might."""

    @property
    def name(self) -> str:
        return "flaky"

    def check(self) -> HealthStatus:
        raise RuntimeError("secret connection string leaked here")


def test_ready_only_when_every_check_is_healthy() -> None:
    report = ReadinessProbe((Fixed("a", True), Fixed("b", True))).check()

    assert report.ready
    assert [c.name for c in report.checks] == ["a", "b"]


def test_one_unhealthy_dependency_makes_the_service_unready() -> None:
    report = ReadinessProbe((Fixed("a", True), Fixed("b", False))).check()

    assert not report.ready
    assert [c.healthy for c in report.checks] == [True, False]


def test_a_raising_check_is_unhealthy_and_does_not_leak_its_message() -> None:
    report = ReadinessProbe((Exploding(), Fixed("a", True))).check()

    assert not report.ready
    assert report.checks[0].detail == "RuntimeError"
    assert "secret connection string" not in str(report)
    assert report.checks[1].healthy


def test_a_service_with_no_dependencies_is_ready() -> None:
    assert ReadinessProbe(()).check().ready
