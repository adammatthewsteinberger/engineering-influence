# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SystemKeepAwake: the platform's inhibitor holds for the block and stops on every way out; without one, the block warns."""

import os
import subprocess

import pytest

from engineering_influence.infrastructure.system_keep_awake import SystemKeepAwake
from engineering_influence.interfaces.keep_awake_interface import KeepAwakeInterface


class Process:
    def __init__(self, ignores_terminate: bool = False) -> None:
        self.ignores_terminate = ignores_terminate
        self.terminated = 0
        self.killed = 0
        self.waits = 0

    def terminate(self) -> None:
        self.terminated += 1

    def kill(self) -> None:
        self.killed += 1

    def wait(self, timeout: float | None = None) -> int:
        self.waits += 1
        if self.ignores_terminate and self.killed == 0 and timeout is not None:
            raise subprocess.TimeoutExpired(cmd="inhibitor", timeout=timeout)
        return 0


class World:
    def __init__(self, system: str, tools: dict[str, str], ignores_terminate: bool = False) -> None:
        self.started: list[list[str]] = []
        self.warnings: list[str] = []
        self.process = Process(ignores_terminate)
        self.awake = SystemKeepAwake(
            system,
            lambda name: tools.get(name),
            self._start,
            self.warnings.append,
        )

    def _start(self, command: list[str]) -> subprocess.Popen[bytes]:
        self.started.append(command)
        return self.process  # type: ignore[return-value]


def test_it_is_a_keep_awake_port() -> None:
    assert isinstance(World("Darwin", {}).awake, KeepAwakeInterface)


def test_on_a_mac_caffeinate_holds_for_the_block_and_is_stopped_after_it() -> None:
    world = World("Darwin", {"caffeinate": "/usr/bin/caffeinate"})
    with world.awake.hold():
        assert world.process.terminated == 0
    assert world.started == [["caffeinate", "-i", "-w", str(os.getpid())]]
    assert world.process.terminated == 1 and world.process.waits == 1
    assert world.warnings == []


def test_the_hold_is_released_when_the_block_fails() -> None:
    world = World("Darwin", {"caffeinate": "/usr/bin/caffeinate"})
    with pytest.raises(RuntimeError, match="the run failed"), world.awake.hold():
        raise RuntimeError("the run failed")
    assert world.process.terminated == 1


def test_an_inhibitor_that_ignores_terminate_is_killed() -> None:
    world = World("Darwin", {"caffeinate": "/usr/bin/caffeinate"}, ignores_terminate=True)
    with world.awake.hold():
        pass
    assert world.process.terminated == 1 and world.process.killed == 1


def test_on_linux_systemd_inhibit_holds_sleep_around_a_sleep() -> None:
    world = World("Linux", {"systemd-inhibit": "/usr/bin/systemd-inhibit"})
    with world.awake.hold():
        pass
    (command,) = world.started
    assert command[0] == "systemd-inhibit" and "--what=sleep" in command
    assert command[-2:] == ["sleep", "infinity"]
    assert world.process.terminated == 1


@pytest.mark.parametrize(
    ("system", "tools"),
    [("Darwin", {}), ("Linux", {}), ("Windows", {"caffeinate": "/x"})],
    ids=["mac-without-caffeinate", "linux-without-systemd", "other-platform"],
)
def test_without_a_tool_the_block_runs_and_the_author_is_warned(
    system: str, tools: dict[str, str]
) -> None:
    world = World(system, tools)
    ran = []
    with world.awake.hold():
        ran.append(True)
    assert ran == [True]
    assert world.started == []
    (warning,) = world.warnings
    assert "may sleep during the run" in warning and "--resume" in warning


def test_the_inhibitor_for_this_machine_is_a_keep_awake() -> None:
    assert isinstance(SystemKeepAwake.for_this_machine(), KeepAwakeInterface)


def test_the_inhibitor_is_started_without_a_shell_and_runs_its_command() -> None:
    import sys

    process = SystemKeepAwake._spawn([sys.executable, "-c", "pass"])
    assert process.wait(timeout=30) == 0


def test_the_warning_goes_to_standard_error(capsys: pytest.CaptureFixture[str]) -> None:
    SystemKeepAwake._warn_on_stderr("a warning")
    assert capsys.readouterr().err == "a warning\n"
