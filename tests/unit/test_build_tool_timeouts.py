# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every build tool runs through the bounded runner, with a deadline it can be stopped at."""

from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.epub.epubcheck_runner import EpubcheckRunner
from engineering_influence.infrastructure.epub.tex4ebook_compiler import Tex4ebookCompiler
from engineering_influence.infrastructure.process.interfaces.process_runner_interface import (
    ProcessRunnerInterface,
)
from engineering_influence.infrastructure.qa.page_rasterizer import PageRasterizer
from engineering_influence.infrastructure.typesetting.latex_compiler import LatexCompiler


class FakeRunner(ProcessRunnerInterface):
    """Records the call, then answers with a canned result or raises the tool's timeout."""

    def __init__(self, result: tuple[int, str, str] = (0, "", ""), stops: bool = False) -> None:
        self.result = result
        self.stops = stops
        self.calls: list[tuple[list[str], float, Path | None, Mapping[str, str] | None]] = []

    def run(
        self,
        command: list[str],
        timeout_seconds: float,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> tuple[int, str, str]:
        self.calls.append((command, timeout_seconds, cwd, env))
        if self.stops:
            raise BookBuildError(f"{command[0]} did not finish within {timeout_seconds:g} seconds")
        return self.result


class FoundEpubcheck(EpubcheckRunner):
    def command(self) -> list[str] | None:
        return ["epubcheck"]


class FoundRenderer(PageRasterizer):
    def command(self) -> str:
        return "pdftoppm"


def latex(runner: FakeRunner, timeout: float | None = None) -> Callable[[Path], object]:
    compiler = LatexCompiler(runner) if timeout is None else LatexCompiler(runner, timeout)
    return lambda tmp: compiler.compile(tmp, "book.tex", 7)


def tex4ebook(runner: FakeRunner, timeout: float | None = None) -> Callable[[Path], object]:
    compiler = Tex4ebookCompiler(runner) if timeout is None else Tex4ebookCompiler(runner, timeout)
    return lambda tmp: compiler.compile(tmp, "book.tex")


def epubcheck(runner: FakeRunner, timeout: float | None = None) -> Callable[[Path], object]:
    made = (
        FoundEpubcheck(runner=runner) if timeout is None else FoundEpubcheck(False, runner, timeout)
    )
    return lambda tmp: made.run(tmp / "book.epub")


def rasterizer(runner: FakeRunner, timeout: float | None = None) -> Callable[[Path], object]:
    made = FoundRenderer(runner) if timeout is None else FoundRenderer(runner, timeout)
    return lambda tmp: made.rasterize(tmp / "a.pdf", tmp / "pages", 90, 3)


TOOLS = {"latexmk": 1800.0, "tex4ebook": 1800.0, "epubcheck": 600.0, "rasterizer": 600.0}
BUILDERS = {
    "latexmk": latex,
    "tex4ebook": tex4ebook,
    "epubcheck": epubcheck,
    "rasterizer": rasterizer,
}


@pytest.mark.parametrize("tool", sorted(TOOLS))
def test_each_tool_gets_its_documented_default_deadline(tool: str, tmp_path: Path) -> None:
    runner = FakeRunner(result=(1, "", "boom"))
    try:
        BUILDERS[tool](runner)(tmp_path)
    except BookBuildError:
        pass  # the rasterizer reports the failed renderer; the deadline is what is checked
    assert [call[1] for call in runner.calls] == [TOOLS[tool]]


@pytest.mark.parametrize("tool", sorted(TOOLS))
def test_a_deadline_can_be_set_per_tool(tool: str, tmp_path: Path) -> None:
    runner = FakeRunner(result=(1, "", "boom"))
    try:
        BUILDERS[tool](runner, 42.5)(tmp_path)
    except BookBuildError:
        pass
    assert [call[1] for call in runner.calls] == [42.5]


@pytest.mark.parametrize("tool", sorted(TOOLS))
def test_a_tool_that_overruns_fails_the_build_with_its_name_and_deadline(
    tool: str, tmp_path: Path
) -> None:
    with pytest.raises(BookBuildError, match="did not finish within 7 seconds"):
        BUILDERS[tool](FakeRunner(stops=True), 7)(tmp_path)


def test_latexmk_runs_without_shell_escape_and_without_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    runner = FakeRunner(result=(0, "ok", "ignored"))
    assert LatexCompiler(runner).compile(tmp_path, "book.tex", 7) == (0, "ok")
    command, _, cwd, env = runner.calls[0]
    assert "-no-shell-escape" in command and cwd == tmp_path
    assert env is not None and "ANTHROPIC_API_KEY" not in env
    assert env["SOURCE_DATE_EPOCH"] == "7"


def test_tex4ebook_runs_in_the_workdir_without_secrets_and_returns_both_streams(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    runner = FakeRunner(result=(0, "out|", "err"))
    assert Tex4ebookCompiler(runner).compile(tmp_path, "book.tex") == (0, "out|err")
    command, _, cwd, env = runner.calls[0]
    assert command[0] == "tex4ebook" and cwd == tmp_path
    assert env is not None and "ANTHROPIC_API_KEY" not in env


def test_epubcheck_findings_come_from_both_streams_without_the_java_banner(
    tmp_path: Path,
) -> None:
    runner = FakeRunner(
        result=(
            1,
            "ERROR(RSC-005): bad\n",
            "Picked up JAVA_TOOL_OPTIONS: -x\nWARNING(OPF-003): stray\n",
        )
    )
    assert FoundEpubcheck(runner=runner).run(tmp_path / "b.epub") == [
        "epubcheck: ERROR(RSC-005): bad",
        "epubcheck: WARNING(OPF-003): stray",
    ]
    assert FoundEpubcheck(runner=FakeRunner()).run(tmp_path / "b.epub") == []
