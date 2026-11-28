# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ProcessRunner: real child processes, because a fake cannot show that a tree is stopped."""

import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.process.interfaces.process_meter_interface import (
    ProcessMeterInterface,
)
from engineering_influence.infrastructure.process.process_meter import ProcessMeter
from engineering_influence.infrastructure.process.process_runner import ProcessRunner
from engineering_influence.models.tool_limits import ToolLimits

BIG = 2**40


def limits(seconds: float, memory: int = BIG, disk: int = BIG) -> ToolLimits:
    return ToolLimits(seconds, memory, disk)


def python(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def wait_until(condition: Callable[[], bool], seconds: float = 10.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return condition()


def pid_in(path: Path) -> int:
    assert wait_until(lambda: path.exists() and path.read_text().strip() != "")
    return int(path.read_text())


def test_a_finished_tool_returns_its_status_and_both_streams() -> None:
    code = "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)"
    assert ProcessRunner().run(python(code), limits(30)) == (3, "out\n", "err\n")


def test_the_tool_runs_in_the_given_directory_with_exactly_the_given_environment(
    tmp_path: Path,
) -> None:
    code = "import os; print(os.getcwd()); print(os.environ.get('EI_X')); print(os.environ.get('HOME'))"
    env: Mapping[str, str] = {"EI_X": "1", "PATH": os.environ["PATH"]}
    status, stdout, _ = ProcessRunner().run(python(code), limits(30), cwd=tmp_path, env=env)
    assert status == 0
    assert stdout.splitlines() == [str(tmp_path.resolve()), "1", "None"]


def test_without_an_environment_the_tool_inherits_the_parents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EI_INHERITED", "yes")
    code = "import os; print(os.environ['EI_INHERITED'])"
    assert ProcessRunner().run(python(code), limits(30))[1] == "yes\n"


def test_a_tool_that_overruns_is_stopped_and_the_error_says_what_it_last_wrote() -> None:
    code = "import time; print('compiling page 12', flush=True); time.sleep(60)"
    started = time.monotonic()
    with pytest.raises(BookBuildError) as caught:
        ProcessRunner().run(python(code), limits(2.0))
    assert time.monotonic() - started < 15
    message = str(caught.value)
    assert f"{sys.executable} did not finish within 2 seconds and was stopped" in message
    assert message.endswith("compiling page 12\n")


def test_the_error_keeps_only_the_tail_of_a_long_output() -> None:
    code = "import time; print('x' * 5000 + 'END', flush=True); time.sleep(60)"
    with pytest.raises(BookBuildError) as caught:
        ProcessRunner().run(python(code), limits(2.0))
    tail = str(caught.value).split("The last output:\n", 1)[1]
    assert len(tail) == ProcessRunner.TAIL_CHARACTERS and tail.endswith("END\n")


SLEEPER = """
import os, sys, time
open(sys.argv[1], "w").write(str(os.getpid()))
time.sleep(60)
"""

SPAWNER = """
import subprocess, sys, time
subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]], start_new_session=sys.argv[3] == "new")
time.sleep(60)
"""


def spawn_a_sleeping_grandchild(tmp_path: Path, session: str) -> tuple[list[str], Path]:
    """A command that starts a sleeping grandchild (in the group, or in a session of its own)."""
    sleeper = tmp_path / "sleeper.py"
    sleeper.write_text(SLEEPER)
    pid_file = tmp_path / "grandchild.pid"
    return [sys.executable, "-c", SPAWNER, str(sleeper), str(pid_file), session], pid_file


def kill_quietly(pid_file: Path) -> None:
    if pid_file.exists() and pid_file.read_text().strip():
        try:
            os.kill(int(pid_file.read_text()), 9)
        except ProcessLookupError:
            pass


def test_everything_the_tool_started_is_stopped_with_it(tmp_path: Path) -> None:
    """latexmk starts lualatex: killing only the direct child would leave it running."""
    command, pid_file = spawn_a_sleeping_grandchild(tmp_path, "same")
    try:
        with pytest.raises(BookBuildError, match="was stopped"):
            ProcessRunner().run(command, limits(3.0))
        pid = pid_in(pid_file)
        assert wait_until(lambda: not alive(pid)), "the grandchild was left running"
    finally:
        kill_quietly(pid_file)


def test_a_process_outside_the_group_cannot_hang_the_run(tmp_path: Path) -> None:
    """Something that left the group still holds the pipes; the read gives up after the drain."""
    command, pid_file = spawn_a_sleeping_grandchild(tmp_path, "new")
    started = time.monotonic()
    try:
        with pytest.raises(BookBuildError, match="was stopped"):
            ProcessRunner(drain_seconds=0.3).run(command, limits(3.0))
        assert time.monotonic() - started < 10
        assert alive(pid_in(pid_file)), "the control did not escape the group"
    finally:
        kill_quietly(pid_file)


def test_an_interrupt_stops_the_tool_instead_of_leaving_it_behind(tmp_path: Path) -> None:
    sleeper = tmp_path / "sleeper.py"
    sleeper.write_text(SLEEPER)
    pid_file = tmp_path / "tool.pid"
    main = threading.main_thread().ident
    assert main is not None

    def interrupt_once_started() -> None:
        pid_in(pid_file)
        signal.pthread_kill(main, signal.SIGINT)  # wakes the blocked read, as Ctrl-C does

    helper = threading.Thread(target=interrupt_once_started)
    helper.start()
    try:
        with pytest.raises(KeyboardInterrupt):
            ProcessRunner().run([sys.executable, str(sleeper), str(pid_file)], limits(60))
    finally:
        helper.join()
        pid = pid_in(pid_file)
    try:
        assert wait_until(lambda: not alive(pid)), "the tool outlived the interrupt"
    finally:
        kill_quietly(pid_file)


def test_stopping_a_group_that_has_already_gone_is_not_an_error() -> None:
    finished = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    finished.wait()
    ProcessRunner()._kill(finished)


def test_a_missing_tool_is_the_callers_error_as_before() -> None:
    with pytest.raises(FileNotFoundError):
        ProcessRunner().run(["definitely-not-a-tool-ei"], limits(5))


class FakeMeter(ProcessMeterInterface):
    """Reports what it is told, and remembers what it was asked."""

    def __init__(self, memory: int = 0, disk: int = 0, started: Path | None = None) -> None:
        self.memory, self.disk = memory, disk
        self.started = started  # until this file exists the tool is still starting: all zero
        self.memory_asked: list[int] = []
        self.disk_asked: list[Path] = []

    def memory_bytes(self, group: int) -> int:
        self.memory_asked.append(group)
        return self.memory if self.up() else 0

    def disk_bytes(self, directory: Path) -> int:
        self.disk_asked.append(directory)
        return self.disk if self.up() else 0

    def up(self) -> bool:
        return self.started is None or (self.started.exists() and self.started.stat().st_size > 0)


MIB = 2**20
SLEEP = "import time; time.sleep(60)"


def test_a_tool_over_its_memory_limit_is_stopped_and_the_error_says_by_how_much(
    tmp_path: Path,
) -> None:
    started = tmp_path / "started"
    code = (
        "from pathlib import Path; print('loading', flush=True); "
        f"Path({str(started)!r}).write_text('x'); " + SLEEP
    )
    meter = FakeMeter(memory=300 * MIB, started=started)
    t0 = time.monotonic()
    with pytest.raises(BookBuildError) as caught:
        ProcessRunner(meter=meter, sample_seconds=0.05).run(
            python(code), limits(30, memory=100 * MIB)
        )
    assert time.monotonic() - t0 < 15
    message = str(caught.value)
    assert (
        f"{sys.executable} used 300 MiB of memory, over its limit of 100 MiB and was stopped"
        in message
    )
    assert message.endswith("loading\n")
    assert len(meter.memory_asked) >= 1


def test_the_memory_measured_is_the_tools_own_process_group(tmp_path: Path) -> None:
    pid_file = tmp_path / "tool.pid"
    code = f"import os; open({str(pid_file)!r}, 'w').write(str(os.getpid())); {SLEEP}"
    meter = FakeMeter(memory=300 * MIB, started=pid_file)
    with pytest.raises(BookBuildError, match="of memory"):
        ProcessRunner(meter=meter, sample_seconds=0.05).run(python(code), limits(30, memory=MIB))
    assert set(meter.memory_asked) == {pid_in(pid_file)}  # a new session: the group id is the pid


def test_a_tool_over_its_disk_limit_is_stopped_when_a_directory_is_watched(tmp_path: Path) -> None:
    meter = FakeMeter(disk=900 * MIB)
    with pytest.raises(BookBuildError) as caught:
        ProcessRunner(meter=meter, sample_seconds=0.05).run(
            python(SLEEP), limits(30, disk=500 * MIB), watch=tmp_path
        )
    assert "wrote 900 MiB to disk, over its limit of 500 MiB and was stopped" in str(caught.value)
    assert set(meter.disk_asked) == {tmp_path}


def test_without_a_watched_directory_disk_is_not_measured() -> None:
    meter = FakeMeter(disk=BIG)
    code = "import time; time.sleep(0.4)"
    assert (
        ProcessRunner(meter=meter, sample_seconds=0.05).run(python(code), limits(30, disk=1))[0]
        == 0
    )
    assert meter.disk_asked == [] and meter.memory_asked != []


def test_a_tool_inside_its_limits_is_left_alone(tmp_path: Path) -> None:
    meter = FakeMeter(memory=MIB, disk=MIB)
    code = "import time; time.sleep(0.4); print('done')"
    status, stdout, _ = ProcessRunner(meter=meter, sample_seconds=0.05).run(
        python(code), limits(30, memory=10 * MIB, disk=10 * MIB), watch=tmp_path
    )
    assert (status, stdout) == (0, "done\n")
    assert len(meter.memory_asked) >= 2 and len(meter.disk_asked) >= 2


def test_a_tool_exactly_at_a_limit_is_not_over_it(tmp_path: Path) -> None:
    meter = FakeMeter(memory=10 * MIB, disk=10 * MIB)
    code = "import time; time.sleep(0.3)"
    runner = ProcessRunner(meter=meter, sample_seconds=0.05)
    assert (
        runner.run(python(code), limits(30, memory=10 * MIB, disk=10 * MIB), watch=tmp_path)[0] == 0
    )


def test_a_tool_that_really_allocates_too_much_is_stopped() -> None:
    code = (
        "import time; data = bytearray(400 * 1024 * 1024); print('allocated', flush=True)\n"
        "while True: data[::4096] = bytes([1]) * len(range(0, len(data), 4096)); time.sleep(0.1)"
    )
    started = time.monotonic()
    with pytest.raises(BookBuildError, match="of memory, over its limit of 150 MiB"):
        ProcessRunner().run(python(code), limits(60, memory=150 * MIB))
    assert time.monotonic() - started < 10  # the default sampling interval is short


ALLOCATOR = """
import os, sys, time
open(sys.argv[1], "w").write(str(os.getpid()))
data = b"x" * (400 * 1024 * 1024)
time.sleep(60)
"""

ALLOCATING_SPAWNER = """
import subprocess, sys, time
subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]])
time.sleep(60)
"""


def test_memory_is_summed_over_everything_the_tool_started(tmp_path: Path) -> None:
    """The tool itself is small; its grandchild is what allocates."""
    allocator = tmp_path / "allocator.py"
    allocator.write_text(ALLOCATOR)
    pid_file = tmp_path / "grandchild.pid"
    command = [sys.executable, "-c", ALLOCATING_SPAWNER, str(allocator), str(pid_file)]
    try:
        with pytest.raises(BookBuildError, match="of memory"):
            ProcessRunner(sample_seconds=0.1).run(command, limits(60, memory=150 * MIB))
        pid = pid_in(pid_file)
        assert wait_until(lambda: not alive(pid)), "the allocating grandchild was left running"
    finally:
        kill_quietly(pid_file)


def test_a_tool_that_really_writes_too_much_is_stopped(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    code = (
        f"import time; open({str(work / 'big.bin')!r}, 'wb').write(b'x' * (30 * 1024 * 1024)); "
        "print('written', flush=True); " + SLEEP
    )
    with pytest.raises(BookBuildError, match="to disk, over its limit of 10 MiB"):
        ProcessRunner(sample_seconds=0.1).run(
            python(code), limits(60, disk=10 * MIB), cwd=work, watch=work
        )


def test_the_default_runner_uses_the_real_meter() -> None:
    runner = ProcessRunner()
    assert isinstance(runner._meter, ProcessMeter)
