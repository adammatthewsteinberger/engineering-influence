"""A run's own output is built into a book with the real toolchain: the idea becomes a PDF, an EPUB, covers and a listing.

This is the proof of bar A2 for a run: no checked-in fixture, but the book that the whole non-fiction plan wrote
(against the scripted local model server of the free rehearsal), built, verified and packaged by the ``build`` stage.
Run with ``uv run pytest -m toolchain``. It needs latexmk, LuaLaTeX, tex4ebook, epubcheck and pdftoppm, so CI runs it
in the toolchain job and a machine without them skips it.
"""

import hashlib
import json
import shutil
import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from local_server import LocalServer
from pypdf import PdfReader
from smoke_rehearsal import AUTHOR, NoSecrets, brief_for, environment, rehearsal, serve
from smoke_run import SmokeReport

from engineering_influence.models.book_kind import BookKind
from engineering_influence.runtime.local_book_runtime import LocalBookRuntime

pytestmark = pytest.mark.toolchain

TOOLS = ("latexmk", "lualatex", "tex4ebook", "epubcheck", "pdftoppm")
SLUG = "herbs-indoors"
BOOK = {
    f"book/{SLUG}.pdf",
    f"book/{SLUG}.epub",
    f"book/{SLUG}-ebook.jpg",
    f"book/{SLUG}-paperback-wrap.pdf",
    "book/listing.md",
    "book/MANIFEST.json",
}


def run_with(
    tmp_path: Path,
    settings: dict[str, str] | None = None,
    kind: BookKind = BookKind.NONFICTION,
) -> SmokeReport:
    missing = [tool for tool in TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"the toolchain is not installed: {', '.join(missing)}")
    server: LocalServer
    with serve() as server:
        return rehearsal(tmp_path, server.url, builder=None, settings=settings, kind=kind).run()


def test_the_whole_plan_ends_in_a_built_book(tmp_path: Path) -> None:
    report = run_with(tmp_path)
    assert report.completed and report.status == "completed", report.issues
    assert [row.stage for row in report.rows][-4:] == ["audit", "build", "audiobook", "narration"]
    files = report.artifacts
    assert BOOK <= set(files)
    assert files[f"book/{SLUG}.pdf"].startswith(b"%PDF")
    assert files[f"book/{SLUG}-ebook.jpg"].startswith(b"\xff\xd8")
    with zipfile.ZipFile(BytesIO(files[f"book/{SLUG}.epub"])) as epub:
        assert epub.namelist()[0] == "mimetype" and epub.testzip() is None


def test_the_quality_report_and_the_manifest_describe_the_files_that_were_built(
    tmp_path: Path,
) -> None:
    files = run_with(tmp_path).artifacts
    quality = json.loads(files["quality-report.json"])
    assert quality["status"] == "pass" and quality["errors"] == []
    assert [step["status"] for step in quality["steps"]] == ["pass"] * len(quality["steps"])
    assert {item["path"] for item in quality["files"]} >= {f"book/{SLUG}.pdf", f"book/{SLUG}.epub"}
    for item in quality["files"]:
        assert item["sha256"] == hashlib.sha256(files[item["path"]]).hexdigest()
        assert item["bytes"] == len(files[item["path"]])
    manifest = json.loads(files["book/MANIFEST.json"])
    assert {entry["name"] for entry in manifest["files"]} >= {f"{SLUG}.pdf", f"{SLUG}.epub"}
    assert "Herbs Indoors" in files["book/listing.md"].decode()


def test_a_strict_release_needs_the_authors_pricing_which_a_run_cannot_invent(
    tmp_path: Path,
) -> None:
    report = run_with(tmp_path, {"EI_BUILD_STRICT_RELEASE": "1"})
    assert not report.completed and report.status == "failed"
    assert report.rows[-1].stage == "build" and report.rows[-1].outcome == "failed"
    assert any("pricing" in issue for issue in report.issues)
    assert json.loads(report.artifacts["quality-report.json"])["status"] == "fail"


def test_a_novel_run_ends_in_a_built_book_at_its_own_trim_size(tmp_path: Path) -> None:
    report = run_with(tmp_path, kind=BookKind.NOVEL)
    assert report.completed and report.status == "completed", report.issues
    assert [row.stage for row in report.rows][-3:] == ["assemble", "audit", "build"]
    files = report.artifacts
    slug = "the-salt-road"
    assert {
        f"book/{slug}.pdf",
        f"book/{slug}.epub",
        "book/listing.md",
        "quality-report.json",
    } <= set(files)
    assert json.loads(files["quality-report.json"])["status"] == "pass"
    page = PdfReader(BytesIO(files[f"book/{slug}.pdf"])).pages[0]
    assert (round(float(page.mediabox.width)), round(float(page.mediabox.height))) == (396, 612)
    with zipfile.ZipFile(BytesIO(files[f"book/{slug}.epub"])) as epub:
        assert epub.testzip() is None


def priced_profile(tmp_path: Path) -> Path:
    """The made-up author of the rehearsal, with the pricing a strict release needs, dated today."""
    path = tmp_path / "priced.toml"
    path.write_text(
        AUTHOR + f'\n[pricing]\nverified_on = "{date.today().isoformat()}"\n'
        'source_url = "https://kdp.amazon.com/en_US/help/topic/G201834170"\n'
        "ebook = 4.99\npaperback = 12.99\nhardcover = 22.99\n",
        encoding="utf-8",
    )
    return path


def test_a_strict_release_passes_when_the_author_supplied_the_pricing(tmp_path: Path) -> None:
    settings = {
        "EI_AUTHOR_PROFILE": str(priced_profile(tmp_path)),
        "EI_BUILD_STRICT_RELEASE": "1",
    }
    report = run_with(tmp_path, settings)
    assert report.completed and report.status == "completed", report.issues
    quality = json.loads(report.artifacts["quality-report.json"])
    assert quality["status"] == "pass" and quality["errors"] == [] and quality["warnings"] == []


def test_book_create_makes_a_whole_book_and_writes_it_to_a_folder(tmp_path: Path) -> None:
    missing = [tool for tool in TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"the toolchain is not installed: {', '.join(missing)}")
    with serve() as server:
        env = environment(
            tmp_path,
            server.url,
            {
                "EI_AUTHOR_PROFILE": str(priced_profile(tmp_path)),
                "EI_BUILD_STRICT_RELEASE": "1",
            },
        )
        creator = LocalBookRuntime(tmp_path / "state", env, NoSecrets())
        try:
            run = creator.start(brief_for(BookKind.NONFICTION), lambda line: None)
            creator.export(tmp_path / "out")
        finally:
            creator.close()
    assert run.status.value == "completed", run.issues
    book = tmp_path / "out" / "run" / "book"
    assert (book / f"{SLUG}.pdf").read_bytes().startswith(b"%PDF")
    assert (book / f"{SLUG}-ebook.jpg").read_bytes().startswith(b"\xff\xd8")
    assert (book / "listing.md").is_file() and (
        tmp_path / "out" / "books" / f"{SLUG}.toml"
    ).is_file()
    with zipfile.ZipFile(book / f"{SLUG}.epub") as epub:
        assert epub.testzip() is None
    assert (
        json.loads((tmp_path / "out" / "run" / "quality-report.json").read_text())["status"]
        == "pass"
    )


def test_a_novel_also_passes_a_strict_release_with_the_authors_pricing(tmp_path: Path) -> None:
    settings = {
        "EI_AUTHOR_PROFILE": str(priced_profile(tmp_path)),
        "EI_BUILD_STRICT_RELEASE": "1",
    }
    report = run_with(tmp_path, settings, kind=BookKind.NOVEL)
    assert report.completed and report.status == "completed", report.issues
    quality = json.loads(report.artifacts["quality-report.json"])
    assert quality["status"] == "pass" and quality["errors"] == []
