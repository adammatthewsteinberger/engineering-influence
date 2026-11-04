"""Evidence helpers: digests, tool versions, git state, inventory, EPUB ZIP, limits, steps."""

import hashlib
import os
import stat
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pypdf import PdfWriter

from engineering_influence.publishing.path_relativizer import PathRelativizer
from engineering_influence.publishing.project_layout import ProjectLayout
from engineering_influence.publishing.readiness_report import ReadinessReport
from engineering_influence.publishing.release.artifact_inventory import ArtifactInventory
from engineering_influence.publishing.release.epub_zip_check import EpubZipCheck
from engineering_influence.publishing.release.file_digest import FileDigest
from engineering_influence.publishing.release.format_policy import FormatPolicy
from engineering_influence.publishing.release.git_state import GitState
from engineering_influence.publishing.release.json_report import JsonReport
from engineering_influence.publishing.release.page_limit_check import PageLimitCheck
from engineering_influence.publishing.release.release_summary import ReleaseSummary
from engineering_influence.publishing.release.step_recorder import StepRecorder
from engineering_influence.publishing.release.tool_versions import ToolVersions


def test_digest_matches_hashlib_across_block_boundaries(tmp_path: Path) -> None:
    data = os.urandom(1024 * 1024 * 2 + 17)
    path = tmp_path / "big.bin"
    path.write_bytes(data)
    assert FileDigest().sha256(path) == hashlib.sha256(data).hexdigest()


def fake_tool(directory: Path, name: str, script: str) -> None:
    directory.mkdir(exist_ok=True)
    path = directory / name
    path.write_text("#!/bin/sh\n" + script, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_tool_versions_use_the_right_flag_and_first_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bin_dir = tmp_path / "bin"
    fake_tool(bin_dir, "latexmk", 'echo "latexmk $1 banner"\necho second line\n')
    fake_tool(bin_dir, "pdftoppm", 'echo "pdftoppm flag $1" >&2\n')
    fake_tool(bin_dir, "tex4ebook", "exit 0\n")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    versions = ToolVersions()
    assert versions.of("latexmk") == "latexmk --version banner"
    assert versions.of("pdftoppm") == "pdftoppm flag -v"
    assert versions.of("tex4ebook") is None  # prints nothing
    assert versions.of("definitely-not-installed-xyz") is None
    env = versions.environment()
    assert env["python"] == sys.version.split()[0] and env["latexmk"] == "latexmk --version banner"
    assert env["epubcheck"] is None or isinstance(env["epubcheck"], str)


def test_tool_versions_survive_a_tool_that_cannot_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_tool(tmp_path / "bin", "latexmk", "sleep 0\n")
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")

    def boom(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired("latexmk", 15)

    monkeypatch.setattr(subprocess, "run", boom)
    assert ToolVersions().of("latexmk") is None


def test_git_state_reads_a_repository_and_tolerates_everything_else(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    for args in (["init", "-q", "-b", "main"], ["commit", "-q", "--allow-empty", "-m", "x"]):
        subprocess.run(["git", *args], cwd=repo, check=True, env=env, capture_output=True)
    (repo / "dirty.txt").write_text("x")
    state = GitState(repo).read()
    assert (
        state["branch"] == "main" and len(state["commit"]) == 40 and "dirty.txt" in state["status"]
    )
    assert GitState(tmp_path / "not-a-repo").read() == {
        "commit": None,
        "branch": None,
        "status": None,
    }
    assert GitState(tmp_path / "missing" / "dir").read()["commit"] is None


def test_format_policy_defaults_keep_old_books_compatible() -> None:
    assert FormatPolicy().of({}) == {"hardcover": False, "hardcover_max_pages": 550}
    assert FormatPolicy().of({"formats": {"hardcover": True, "hardcover_max_pages": "300"}}) == {
        "hardcover": True,
        "hardcover_max_pages": 300,
    }


def test_inventory_lists_required_artifacts_and_reports_missing_ones(tmp_path: Path) -> None:
    layout = ProjectLayout(tmp_path)
    (layout.output / "covers" / "demo").mkdir(parents=True)
    (layout.output / "demo.pdf").write_bytes(b"%PDF")
    inventory = ArtifactInventory(layout)
    plain = inventory.artifacts("demo")
    assert [a["kind"] for a in plain] == [
        "pdf-interior",
        "epub",
        "ebook-cover",
        "paperback-wrap",
        "hardcover-wrap",
    ]
    assert (
        plain[0]["exists"]
        and plain[0]["bytes"] == 4
        and plain[0]["sha256"] == hashlib.sha256(b"%PDF").hexdigest()
    )
    assert plain[0]["path"] == "output/demo.pdf" and "sha256" not in plain[1]
    assert inventory.problems(plain)[0] == "missing artifact: output/demo.epub"
    assert len(inventory.problems(plain)) == 4
    hard = inventory.artifacts("demo", hardcover=True)
    assert [a["kind"] for a in hard][1] == "hardcover-interior"


def make_epub(path: Path, *, stored: bool = True, first: str = "mimetype") -> Path:
    with zipfile.ZipFile(path, "w") as z:
        kind = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
        z.writestr(first, "application/epub+zip", compress_type=kind)
        z.writestr("x.xhtml", "<html/>")
    return path


def test_epub_zip_check(tmp_path: Path) -> None:
    check = EpubZipCheck()
    assert check.run(make_epub(tmp_path / "ok.epub")) == []
    assert "missing EPUB" in check.run(tmp_path / "absent.epub")[0]
    assert check.run(make_epub(tmp_path / "late.epub", first="other")) == [
        "EPUB ZIP must keep mimetype as its first member"
    ]
    assert check.run(make_epub(tmp_path / "packed.epub", stored=False)) == [
        "EPUB mimetype member must be uncompressed"
    ]
    junk = tmp_path / "junk.epub"
    junk.write_bytes(b"not a zip")
    assert "EPUB ZIP validation failed" in check.run(junk)[0]
    empty = tmp_path / "empty.epub"
    with zipfile.ZipFile(empty, "w"):
        pass
    assert check.run(empty) == ["EPUB ZIP must keep mimetype as its first member"]


def test_epub_zip_check_reports_a_corrupt_member(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(zipfile.ZipFile, "testzip", lambda self: "x.xhtml")
    assert EpubZipCheck().run(make_epub(tmp_path / "bad.epub")) == [
        "EPUB ZIP integrity failed at x.xhtml"
    ]


def pdf_with(path: Path, pages: int) -> Path:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(100, 100)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def test_page_limit_check(tmp_path: Path) -> None:
    check = PageLimitCheck()
    assert check.run(tmp_path / "absent.pdf", label="x", maximum=5) is None
    pdf = pdf_with(tmp_path / "a.pdf", 3)
    assert check.run(pdf, label="hardcover interior", maximum=3) is None
    assert check.run(pdf, label="hardcover interior", maximum=2) == (
        "hardcover interior has 3 pages; configured maximum is 2"
    )


def test_json_report_creates_parents_and_controls_ascii(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "r.json"
    JsonReport().write(path, {"n": "é"})
    assert path.read_text(encoding="utf-8") == '{\n  "n": "é"\n}\n'
    JsonReport().write(path, {"n": "é"}, ensure_ascii=True)
    assert '"\\u00e9"' in path.read_text(encoding="utf-8")


def test_release_summary_flattens_findings() -> None:
    report = ReadinessReport(
        1, "demo", "warning", "demo.toml", None, pricing={"a": 1}, formats={"b": 2}
    )
    report.add("warning", "code", "msg", "path")
    assert ReleaseSummary().of(report, "r.json") == {
        "status": "warning",
        "report": "r.json",
        "findings": [{"severity": "warning", "code": "code", "message": "msg", "path": "path"}],
        "pricing": {"a": 1},
        "formats": {"b": 2},
    }


def test_step_recorder_records_passes_and_failures(tmp_path: Path) -> None:
    ticks = iter(datetime(2031, 1, 1, 0, 0, s, tzinfo=UTC) for s in range(10))
    recorder = StepRecorder(PathRelativizer(tmp_path), lambda: next(ticks))
    ok = recorder.run("pdf", ["do", "it"], lambda: "all good\n" * 1000, tmp_path / "pdf.log")
    assert ok["status"] == "pass" and ok["returncode"] == 0 and len(ok["stdout_tail"]) == 4000
    assert (
        ok["started_at"] == "2031-01-01T00:00:00+00:00"
        and ok["finished_at"] == "2031-01-01T00:00:01+00:00"
    )
    assert ok["log"] == "pdf.log" and (tmp_path / "pdf.log").read_text().startswith("all good")

    def explode() -> str:
        raise ValueError("LaTeX failed: line 7")

    bad = recorder.run("epub", ["x"], explode, tmp_path / "epub.log")
    assert (
        bad["status"] == "fail"
        and bad["returncode"] == 1
        and bad["stdout_tail"] == "LaTeX failed: line 7"
    )
    assert (tmp_path / "epub.log").read_text() == "LaTeX failed: line 7"


def test_step_recorder_uses_the_real_clock_by_default(tmp_path: Path) -> None:
    record = StepRecorder(PathRelativizer(tmp_path)).run("x", [], lambda: "", tmp_path / "x.log")
    assert record["started_at"].endswith("+00:00")
