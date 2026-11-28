# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Linux command: private namespaces, no host sockets, the home directory replaced, one writable directory."""

from pathlib import Path

from engineering_influence.infrastructure.tools.bubblewrap_command import BubblewrapCommand
from engineering_influence.infrastructure.tools.sandbox_allowance import SandboxAllowance


def test_the_server_is_confined_with_private_sockets_and_home_replaced(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    place = str(work.resolve())
    wrapped = BubblewrapCommand("/usr/bin/bwrap", home, SandboxAllowance()).wrap(
        ("/bin/server", "--stdio"), work
    )
    assert wrapped == (
        "/usr/bin/bwrap",
        "--die-with-parent",
        "--new-session",
        "--unshare-net",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--cap-drop",
        "ALL",
        "--ro-bind",
        "/",
        "/",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--perms",
        "0555",
        "--tmpfs",
        "/run",
        "--perms",
        "0555",
        "--tmpfs",
        "/tmp",
        "--perms",
        "0555",
        "--tmpfs",
        str(home.resolve()),
        "--bind",
        place,
        place,
        "--chdir",
        place,
        "--",
        "/bin/server",
        "--stdio",
    )


def test_an_allowed_interpreter_directory_is_bound_back_read_only_over_the_home_replacement(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    venv = home / "proj" / ".venv"
    (venv / "bin").mkdir(parents=True)
    work = tmp_path / "work"
    work.mkdir()
    wrapped = BubblewrapCommand("/usr/bin/bwrap", home, SandboxAllowance()).wrap(
        (str(venv / "bin" / "python3"),), work
    )
    home_at = wrapped.index("--tmpfs", wrapped.index(str(home.resolve())) - 1)
    bound = wrapped.index("--ro-bind", home_at)
    assert wrapped[bound : bound + 3] == ("--ro-bind", str(venv.resolve()), str(venv.resolve()))
