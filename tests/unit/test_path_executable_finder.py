# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""PathExecutableFinder: a name is looked up on PATH, a path is made absolute, and only executables count."""

import os
from pathlib import Path

import pytest

from engineering_influence.infrastructure.tools.path_executable_finder import PathExecutableFinder
from engineering_influence.interfaces.executable_finder_interface import ExecutableFinderInterface


def make(path: Path, executable: bool = True) -> Path:
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    path.chmod(0o755 if executable else 0o644)
    return path


def test_it_is_an_executable_finder() -> None:
    assert isinstance(PathExecutableFinder(), ExecutableFinderInterface)


def test_a_name_is_looked_up_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tool = make(tmp_path / "my-server")
    monkeypatch.setenv("PATH", str(tmp_path))
    assert PathExecutableFinder().find("my-server") == str(tool)


def test_a_path_is_made_absolute_from_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make(tmp_path / "server")
    monkeypatch.chdir(tmp_path)
    assert PathExecutableFinder().find("./server") == str(Path(os.getcwd()) / "server")


def test_an_absolute_path_is_returned_as_given(tmp_path: Path) -> None:
    tool = make(tmp_path / "server")
    assert PathExecutableFinder().find(str(tool)) == str(tool)


def test_a_symbolic_link_is_not_followed(tmp_path: Path) -> None:
    real = make(tmp_path / "real")
    link = tmp_path / "link"
    link.symlink_to(real)
    assert PathExecutableFinder().find(str(link)) == str(link)


@pytest.mark.parametrize("kind", ["missing", "not executable", "directory"])
def test_what_is_not_an_executable_file_is_not_found(tmp_path: Path, kind: str) -> None:
    target = tmp_path / "thing"
    if kind == "not executable":
        make(target, executable=False)
    elif kind == "directory":
        target.mkdir()
    assert PathExecutableFinder().find(str(target)) is None


def test_a_name_that_is_nowhere_on_path_is_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    assert PathExecutableFinder().find("no-such-command-anywhere") is None
