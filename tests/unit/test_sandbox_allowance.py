# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A server may read the directories its own interpreter and files live in, below home, and nothing else there."""

from pathlib import Path

from engineering_influence.infrastructure.tools.sandbox_allowance import SandboxAllowance


def test_a_virtual_environment_and_its_interpreter_are_allowed_below_home(tmp_path: Path) -> None:
    home = tmp_path / "home"
    venv = home / "proj" / ".venv"
    (venv / "bin").mkdir(parents=True)
    base = home / ".local" / "share" / "uv" / "python" / "cpython-3.13"
    (base / "bin").mkdir(parents=True)
    real = base / "bin" / "python3.13"
    real.write_text("")
    link = venv / "bin" / "python3"
    link.symlink_to(real)
    allowed = SandboxAllowance().paths((str(link), "--stdio"), home)
    for directory in (venv, venv / "bin", base, base / "bin"):
        assert directory.resolve() in allowed


def test_the_home_directory_itself_is_never_allowed(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / "bin").mkdir(parents=True)
    assert SandboxAllowance().paths((str(home / "bin" / "server"),), home) == (
        (home / "bin").resolve(),
    )


def test_a_path_outside_home_adds_nothing(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    assert SandboxAllowance().paths(("/usr/bin/python3", "--stdio"), home) == ()


def test_arguments_that_are_not_paths_add_nothing(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    assert SandboxAllowance().paths(("python3", "--stdio", "https://x"), home) == ()


def test_the_allowance_is_in_name_order_and_each_directory_once(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / "a").mkdir(parents=True)
    paths = SandboxAllowance().paths((str(home / "a" / "x"), str(home / "a" / "y")), home)
    assert paths == tuple(sorted(set(paths)))
    assert paths.count(home / "a") == 1
