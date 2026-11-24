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
from io import BytesIO
from pathlib import Path

import pytest
from local_server import LocalServer
from smoke_rehearsal import rehearsal, serve
from smoke_run import SmokeReport

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


def run_with(tmp_path: Path, settings: dict[str, str] | None = None) -> SmokeReport:
    missing = [tool for tool in TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"the toolchain is not installed: {', '.join(missing)}")
    server: LocalServer
    with serve() as server:
        return rehearsal(tmp_path, server.url, builder=None, settings=settings).run()


def test_the_whole_plan_ends_in_a_built_book(tmp_path: Path) -> None:
    report = run_with(tmp_path)
    assert report.completed and report.status == "completed", report.issues
    assert [row.stage for row in report.rows][-2:] == ["audit", "build"]
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
