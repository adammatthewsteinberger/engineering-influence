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
from engineering_influence.infrastructure.process.process_runner import ProcessRunner


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
    assert ProcessRunner().run(python(code), 30) == (3, "out\n", "err\n")


def test_the_tool_runs_in_the_given_directory_with_exactly_the_given_environment(
    tmp_path: Path,
) -> None:
    code = "import os; print(os.getcwd()); print(os.environ.get('EI_X')); print(os.environ.get('HOME'))"
    env: Mapping[str, str] = {"EI_X": "1", "PATH": os.environ["PATH"]}
    status, stdout, _ = ProcessRunner().run(python(code), 30, cwd=tmp_path, env=env)
    assert status == 0
    assert stdout.splitlines() == [str(tmp_path.resolve()), "1", "None"]


def test_without_an_environment_the_tool_inherits_the_parents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EI_INHERITED", "yes")
    code = "import os; print(os.environ['EI_INHERITED'])"
    assert ProcessRunner().run(python(code), 30)[1] == "yes\n"


def test_a_tool_that_overruns_is_stopped_and_the_error_says_what_it_last_wrote() -> None:
    code = "import time; print('compiling page 12', flush=True); time.sleep(60)"
    started = time.monotonic()
    with pytest.raises(BookBuildError) as caught:
        ProcessRunner().run(python(code), 0.5)
    assert time.monotonic() - started < 15
    message = str(caught.value)
    assert f"{sys.executable} did not finish within 0.5 seconds and was stopped" in message
    assert message.endswith("compiling page 12\n")


def test_the_error_keeps_only_the_tail_of_a_long_output() -> None:
    code = "import time; print('x' * 5000 + 'END', flush=True); time.sleep(60)"
    with pytest.raises(BookBuildError) as caught:
        ProcessRunner().run(python(code), 0.5)
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
            ProcessRunner().run(command, 1.5)
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
            ProcessRunner(drain_seconds=0.3).run(command, 1.5)
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
            ProcessRunner().run([sys.executable, str(sleeper), str(pid_file)], 60)
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
        ProcessRunner().run(["definitely-not-a-tool-ei"], 5)
