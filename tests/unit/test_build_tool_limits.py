# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every build tool runs through the bounded runner, under limits it can be stopped at."""

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
from engineering_influence.models.tool_limits import ToolLimits

GIB = 2**30


class Call:
    def __init__(
        self,
        command: list[str],
        limits: ToolLimits,
        cwd: Path | None,
        env: Mapping[str, str] | None,
        watch: Path | None,
    ) -> None:
        self.command, self.limits, self.cwd, self.env, self.watch = command, limits, cwd, env, watch


class FakeRunner(ProcessRunnerInterface):
    """Records the call, then answers with a canned result or raises the tool's overrun."""

    def __init__(self, result: tuple[int, str, str] = (0, "", ""), stops: bool = False) -> None:
        self.result = result
        self.stops = stops
        self.calls: list[Call] = []

    def run(
        self,
        command: list[str],
        limits: ToolLimits,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        watch: Path | None = None,
    ) -> tuple[int, str, str]:
        self.calls.append(Call(command, limits, cwd, env, watch))
        if self.stops:
            raise BookBuildError(f"{command[0]} passed a limit and was stopped")
        return self.result


class FoundEpubcheck(EpubcheckRunner):
    def command(self) -> list[str] | None:
        return ["epubcheck"]


class FoundRenderer(PageRasterizer):
    def command(self) -> str:
        return "pdftoppm"


def latex(runner: FakeRunner, limits: ToolLimits | None, tmp: Path) -> object:
    return LatexCompiler(runner, limits).compile(tmp, "book.tex", 7)


def tex4ebook(runner: FakeRunner, limits: ToolLimits | None, tmp: Path) -> object:
    return Tex4ebookCompiler(runner, limits).compile(tmp, "book.tex")


def epubcheck(runner: FakeRunner, limits: ToolLimits | None, tmp: Path) -> object:
    return FoundEpubcheck(False, runner, limits).run(tmp / "book.epub")


def rasterizer(runner: FakeRunner, limits: ToolLimits | None, tmp: Path) -> object:
    return FoundRenderer(runner, limits).rasterize(tmp / "a.pdf", tmp / "pages", 90, 3)


# tool -> (how to run it, its documented default limits, whether it asks for a directory watch)
TOOLS: dict[str, tuple[Callable[[FakeRunner, ToolLimits | None, Path], object], ToolLimits]] = {
    "latexmk": (latex, ToolLimits(1800.0, 8 * GIB, 4 * GIB)),
    "tex4ebook": (tex4ebook, ToolLimits(1800.0, 8 * GIB, 4 * GIB)),
    "epubcheck": (epubcheck, ToolLimits(600.0, 4 * GIB, 1 * GIB)),
    "rasterizer": (rasterizer, ToolLimits(600.0, 2 * GIB, 4 * GIB)),
}


def run_ignoring_a_failed_tool(
    tool: str, runner: FakeRunner, limits: ToolLimits | None, tmp: Path
) -> None:
    try:
        TOOLS[tool][0](runner, limits, tmp)
    except BookBuildError:
        pass  # the rasterizer reports a failed renderer; the limits are what is checked


@pytest.mark.parametrize("tool", sorted(TOOLS))
def test_each_tool_gets_its_documented_default_limits(tool: str, tmp_path: Path) -> None:
    runner = FakeRunner(result=(1, "", "boom"))
    run_ignoring_a_failed_tool(tool, runner, None, tmp_path)
    assert [(c.limits) for c in runner.calls] == [TOOLS[tool][1]]


@pytest.mark.parametrize("tool", sorted(TOOLS))
def test_limits_can_be_set_per_tool(tool: str, tmp_path: Path) -> None:
    mine = ToolLimits(42.5, 123456, 654321)
    runner = FakeRunner(result=(1, "", "boom"))
    run_ignoring_a_failed_tool(tool, runner, mine, tmp_path)
    assert [c.limits for c in runner.calls] == [mine]


@pytest.mark.parametrize("tool", sorted(TOOLS))
def test_a_tool_that_passes_a_limit_fails_the_build(tool: str, tmp_path: Path) -> None:
    with pytest.raises(BookBuildError, match="passed a limit and was stopped"):
        TOOLS[tool][0](FakeRunner(stops=True), None, tmp_path)


def test_the_disk_watch_is_the_directory_each_tool_writes_into(tmp_path: Path) -> None:
    seen = {}
    for tool in TOOLS:
        runner = FakeRunner(result=(1, "", "boom"))
        run_ignoring_a_failed_tool(tool, runner, None, tmp_path)
        seen[tool] = runner.calls[0].watch
    assert seen == {
        "latexmk": tmp_path,
        "tex4ebook": tmp_path,
        "epubcheck": None,  # it writes nothing
        "rasterizer": tmp_path / "pages",
    }


def test_latexmk_runs_without_shell_escape_and_without_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    runner = FakeRunner(result=(0, "ok", "ignored"))
    assert LatexCompiler(runner).compile(tmp_path, "book.tex", 7) == (0, "ok")
    call = runner.calls[0]
    assert "-no-shell-escape" in call.command and call.cwd == tmp_path
    assert call.env is not None and "ANTHROPIC_API_KEY" not in call.env
    assert call.env["SOURCE_DATE_EPOCH"] == "7"


def test_tex4ebook_runs_in_the_workdir_without_secrets_and_returns_both_streams(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    runner = FakeRunner(result=(0, "out|", "err"))
    assert Tex4ebookCompiler(runner).compile(tmp_path, "book.tex") == (0, "out|err")
    call = runner.calls[0]
    assert call.command[0] == "tex4ebook" and call.cwd == tmp_path
    assert call.env is not None and "ANTHROPIC_API_KEY" not in call.env


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
