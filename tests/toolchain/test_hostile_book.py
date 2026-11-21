"""A book full of hostile text builds with the real toolchain and executes none of it.

Every text field of a copy of the fixture book carries a payload that, if any of it reached
TeX unescaped, would write a file in the build directory: one by TeX's own ``\\openout`` and one
by Lua's ``io.open`` through ``\\directlua``. Neither needs shell escape, so the test proves the
text is escaped and not merely that shell escape is switched off. Run with
``uv run pytest -m toolchain``; a machine without the TeX tools skips it.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from engineering_influence.infrastructure.epub.tex4ebook_compiler import Tex4ebookCompiler
from engineering_influence.infrastructure.publishing.package_assets import PackageAssets
from engineering_influence.infrastructure.typesetting.filesystem_build_workspace import (
    FilesystemBuildWorkspace,
)
from engineering_influence.infrastructure.typesetting.latex_compiler import LatexCompiler

pytestmark = pytest.mark.toolchain

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "fixture_book"
TOOLS = ("latexmk", "lualatex", "tex4ebook")
# Closing braces end any group the text sits in; the rest writes two canary files.
PAYLOAD = (
    r"}}}\immediate\openout3=EICANARYTEX\relax\immediate\write3{x}\immediate\closeout3 "
    r'\directlua{io.open("EICANARYLUA","w"):write("x")}{{{'
).replace(" ", "")
HOSTILE_BODY = f"""# Chapter 1: The Keeper

{PAYLOAD}

## {PAYLOAD}

- {PAYLOAD}

| a | b |
|---|---|
| {PAYLOAD} | x |

> {PAYLOAD}

See https://x.test/{PAYLOAD} and https://x.test/a\\EIcanary for more.
"""


def hostile_root(tmp_path: Path, hostile_title: bool = True) -> Path:
    shutil.copytree(FIXTURE / "src", tmp_path / "src")
    shutil.copytree(FIXTURE / "books", tmp_path / "books")
    (tmp_path / "src" / "01-first.md").write_text(HOSTILE_BODY, encoding="utf-8")
    config = tmp_path / "books" / "fixture.toml"
    text = config.read_text(encoding="utf-8")
    fields = ("title", "subtitle", "author", "publisher", "edition")
    for field in fields:
        if field == "title" and not hostile_title:
            continue
        text = text.replace(f'{field} = "', f"{field} = '{PAYLOAD}", 1)
        line = next(line for line in text.splitlines() if line.startswith(f"{field} = '"))
        text = text.replace(line, line.rstrip('"') + "'", 1)
    text = text.replace(
        'author_bio = "',
        f"website = 'https://x.test/{PAYLOAD}'\n"
        f"email = 'a{PAYLOAD}@x.test'\n"
        f"dedication = '{PAYLOAD}'\n"
        f"copyright_notes = '{PAYLOAD}'\n"
        'author_bio = "',
        1,
    )
    text = text.replace('"Part One: Light"', f"'Part One: {PAYLOAD}'")
    config.write_text(text, encoding="utf-8")
    return tmp_path


def run(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-m",
        "engineering_influence",
        "book",
        "--root",
        str(root),
        *arguments,
    ]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def need_tools() -> None:
    missing = [tool for tool in TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"the TeX toolchain is not installed: {', '.join(missing)}")


def test_hostile_text_builds_into_a_pdf_and_runs_nothing(tmp_path: Path) -> None:
    need_tools()
    root = hostile_root(tmp_path)
    pdf = run(root, "build", "fixture", "--no-verify")
    assert pdf.returncode == 0, pdf.stdout + pdf.stderr

    written = sorted(path.name for path in root.rglob("EICANARY*"))
    assert written == [], f"hostile text ran and wrote {written}"
    assert not list(Path.cwd().glob("EICANARY*"))

    built = next(root.rglob("fixture.pdf"))
    pages = " ".join(page.extract_text() or "" for page in PdfReader(built).pages)
    # The payload is printed as text, so it is visible to a reader and inert.
    assert "EICANARYTEX" in pages.replace(" ", "").replace("\n", "")


def test_hostile_text_builds_into_an_epub_and_runs_nothing(tmp_path: Path) -> None:
    """Every field but the title, which the ebook builder refuses outright (next test)."""
    need_tools()
    root = hostile_root(tmp_path, hostile_title=False)
    # The ebook needs its cover image; a plain one keeps the covers pipeline, which has its own
    # text-fit check that these absurdly long fields would trip, out of this test.
    cover = root / "output" / "covers" / "fixture" / "fixture-ebook.jpg"
    cover.parent.mkdir(parents=True)
    Image.new("RGB", (1600, 2560), "white").save(cover)
    epub = run(root, "epub", "fixture", "--no-verify")
    assert epub.returncode == 0, epub.stdout + epub.stderr
    written = sorted(path.name for path in root.rglob("EICANARY*"))
    assert written == [], f"hostile text ran and wrote {written}"
    assert not list(Path.cwd().glob("EICANARY*"))


def test_a_hostile_title_stops_the_ebook_build_before_tex(tmp_path: Path) -> None:
    root = hostile_root(tmp_path)
    result = run(root, "epub", "fixture", "--tex-only")
    assert result.returncode != 0
    assert "cannot carry" in result.stdout + result.stderr
    assert list(root.rglob("EICANARY*")) == []


def test_a_code_block_that_would_end_its_environment_stops_the_build_before_tex(
    tmp_path: Path,
) -> None:
    root = hostile_root(tmp_path)
    (root / "src" / "01-first.md").write_text(
        "# Chapter 1: The Keeper\n\n```\n\\end{verbatim}\\immediate\\openout3=EICANARYTEX\n```\n",
        encoding="utf-8",
    )
    result = run(root, "build", "fixture", "--tex-only")
    assert result.returncode != 0
    assert "verbatim" in result.stdout + result.stderr
    assert list(root.rglob("EICANARY*")) == []


LIVE_TEX = r"""\documentclass{article}
\begin{document}
\immediate\openout3=EICANARYOPEN\relax\immediate\write3{x}\immediate\closeout3
\immediate\write18{touch EICANARYSHELL}
Hello.
\end{document}
"""


def live_workdir(tmp_path: Path, ebook: bool) -> Path:
    """A build directory holding a document that deliberately runs a file write and a shell command."""
    workdir = tmp_path / "live"
    if ebook:
        with PackageAssets().directory() as assets:
            FilesystemBuildWorkspace().prepare_ebook(workdir, assets)
        # The ebook configuration reads this file, which the real build generates per book.
        (workdir / "ebook-meta.tex").write_text(
            "\\def\\EbookIdentifier{urn:uuid:00000000-0000-0000-0000-000000000000}"
            "\\def\\EbookTitle{Live}\n",
            encoding="utf-8",
        )
    else:
        workdir.mkdir()
    (workdir / "live.tex").write_text(LIVE_TEX, encoding="utf-8")
    return workdir


def test_live_tex_runs_a_file_write_but_never_a_shell_command_in_lualatex(tmp_path: Path) -> None:
    """The positive control: the canary does detect live TeX, and shell escape is off anyway."""
    need_tools()
    workdir = live_workdir(tmp_path, ebook=False)
    LatexCompiler().compile(workdir, "live.tex", 0)
    # TeX appends ".tex" to the name it is given.
    assert list(workdir.glob("EICANARYOPEN*")), "the canary technique cannot detect live TeX"
    assert not list(workdir.glob("EICANARYSHELL*")), "LuaLaTeX ran a shell command"


def test_live_tex_runs_a_file_write_but_never_a_shell_command_in_tex4ebook(tmp_path: Path) -> None:
    need_tools()
    workdir = live_workdir(tmp_path, ebook=True)
    Tex4ebookCompiler().compile(workdir, "live.tex")
    assert list(workdir.glob("EICANARYOPEN*")), "the canary technique cannot detect live TeX"
    assert not list(workdir.glob("EICANARYSHELL*")), "tex4ebook ran a shell command"
