# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Linux command: fresh network and process namespaces, a read-only system, one writable directory."""

from pathlib import Path

from engineering_influence.infrastructure.tools.bubblewrap_command import BubblewrapCommand


def test_the_server_runs_in_its_own_namespaces_with_one_writable_directory(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    place = str(work.resolve())
    assert BubblewrapCommand("/usr/bin/bwrap").wrap(("/bin/server", "--stdio"), work) == (
        "/usr/bin/bwrap",
        "--die-with-parent",
        "--unshare-net",
        "--unshare-pid",
        "--ro-bind",
        "/",
        "/",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--bind",
        place,
        place,
        "--chdir",
        place,
        "--",
        "/bin/server",
        "--stdio",
    )
