# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A build that never finishes is stopped, with every process it started, by the real tools.

``\\def\\x{\\x}\\x`` expands to itself without growing TeX's stack, so TeX never errors and never
exits: the build hangs for as long as it is allowed to. The document first writes a marker, so a
passing test shows the tool really reached the loop and was stopped there, not that the deadline
passed before TeX started. Run with ``uv run pytest -m toolchain``; a machine without the TeX
tools skips it.
"""

import shutil
import subprocess
import time
import uuid
from collections.abc import Callable
from pathlib import Path

import pytest

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.epub.tex4ebook_compiler import Tex4ebookCompiler
from engineering_influence.infrastructure.publishing.package_assets import PackageAssets
from engineering_influence.infrastructure.typesetting.filesystem_build_workspace import (
    FilesystemBuildWorkspace,
)
from engineering_influence.infrastructure.typesetting.latex_compiler import LatexCompiler

pytestmark = pytest.mark.toolchain

TOOLS = ("latexmk", "lualatex", "tex4ebook", "pgrep")
DEADLINE = 10.0


def hanging_document(name: str) -> str:
    return (
        "\\documentclass{article}\n\\begin{document}\n"
        "\\immediate\\openout3=started.txt\\relax\\immediate\\write3{x}\\immediate\\closeout3\n"
        f"% {name}\n\\def\\x{{\\x}}\\x\n\\end{{document}}\n"
    )


def need_tools() -> None:
    missing = [tool for tool in TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"the TeX toolchain is not installed: {', '.join(missing)}")


def running(name: str) -> bool:
    """Whether any process on this machine still has the job name in its command line."""
    return subprocess.run(["pgrep", "-f", name], capture_output=True, check=False).returncode == 0


def assert_stopped_and_gone(build: Callable[[], object], workdir: Path, name: str) -> None:
    started = time.monotonic()
    with pytest.raises(BookBuildError, match=f"did not finish within {DEADLINE:g} seconds"):
        build()
    assert time.monotonic() - started < DEADLINE + 30, "the stop took far longer than the deadline"
    assert (workdir / "started.txt").exists(), "TeX never reached the loop"
    deadline = time.monotonic() + 15
    while running(name) and time.monotonic() < deadline:
        time.sleep(0.2)
    assert not running(name), "a process the build started is still running"


def test_a_hanging_lualatex_build_is_stopped_with_everything_latexmk_started(
    tmp_path: Path,
) -> None:
    need_tools()
    name = f"hang{uuid.uuid4().hex[:12]}"
    (tmp_path / f"{name}.tex").write_text(hanging_document(name), encoding="utf-8")
    compiler = LatexCompiler(timeout_seconds=DEADLINE)
    assert_stopped_and_gone(lambda: compiler.compile(tmp_path, f"{name}.tex", 0), tmp_path, name)


def test_a_hanging_ebook_build_is_stopped_with_everything_tex4ebook_started(
    tmp_path: Path,
) -> None:
    need_tools()
    name = f"hang{uuid.uuid4().hex[:12]}"
    workdir = tmp_path / "ebook"
    with PackageAssets().directory() as assets:
        FilesystemBuildWorkspace().prepare_ebook(workdir, assets)
    (workdir / "ebook-meta.tex").write_text(
        "\\def\\EbookIdentifier{urn:uuid:00000000-0000-0000-0000-000000000000}"
        "\\def\\EbookTitle{Hang}\n",
        encoding="utf-8",
    )
    (workdir / f"{name}.tex").write_text(hanging_document(name), encoding="utf-8")
    compiler = Tex4ebookCompiler(timeout_seconds=DEADLINE)
    assert_stopped_and_gone(lambda: compiler.compile(workdir, f"{name}.tex"), workdir, name)
