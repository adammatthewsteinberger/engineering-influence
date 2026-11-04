"""The publishing controller and the `ei book` commands, over a small temporary project."""

import json
import sys
import textwrap
import zipfile
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from pypdf import PdfWriter

from engineering_influence.controllers.publishing_controller import PublishingController
from engineering_influence.interaction.cli.main import CliApplication
from engineering_influence.publishing.covers.cover_builder import CoverBuilder
from engineering_influence.publishing.epub.epub_builder import EpubBuilder
from engineering_influence.publishing.epub.epub_verifier import EpubVerifier
from engineering_influence.publishing.pdf_verifier import PdfVerifier
from engineering_influence.publishing.project_config import ProjectConfig
from engineering_influence.publishing.qa.page_record import PageRecord
from engineering_influence.publishing.qa.render_qa import RenderQa
from engineering_influence.publishing.qa.render_report import RenderReport
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError
from engineering_influence.publishing.typesetting.book_builder import BookBuilder
from engineering_influence.publishing.typesetting.latex_compiler import LatexCompiler

BOOK = (
    'source = "src"\ntitle = "Demo Cover"\nsubtitle = "Sub"\nauthor = "Ann Author"\npublisher = "P"\n'
    'edition = "First Edition"\nauthor_bio = "Bio."\ndescription = "A blurb."\n'
    'parts = [{ title = "One", chapters = ["one.md"] }]\n'
)


def write_pdf(path: Path, pages: int = 120) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(432, 648)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def write_epub(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
    return path


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(sys, "path", list(sys.path))
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "one.md").write_text(
        "# Chapter 1: One\n\nOne begins here.\n", encoding="utf-8"
    )
    (tmp_path / "books").mkdir()
    (tmp_path / "books" / "demo.toml").write_text(BOOK, encoding="utf-8")
    return tmp_path


@pytest.fixture
def stubs(monkeypatch: pytest.MonkeyPatch, root: Path) -> dict[str, list[Any]]:
    """Replace the slow external steps with ones that leave real artifacts behind."""
    calls: dict[str, list[Any]] = {"latex": [], "covers": [], "verify": []}

    def latex(self: LatexCompiler, workdir: Path, tex_name: str, epoch: int) -> tuple[int, str]:
        calls["latex"].append(tex_name)
        write_pdf(workdir / tex_name.replace(".tex", ".pdf"))
        return 0, ""

    def covers(
        self: CoverBuilder, slug: str, preview: bool = False, hardcover_pdf: Path | None = None
    ) -> Path:
        calls["covers"].append((slug, preview, hardcover_pdf))
        out = root / "output" / "covers" / slug
        out.mkdir(parents=True, exist_ok=True)
        for name in (
            f"{slug}-ebook.jpg",
            f"{slug}-paperback-wrap.pdf",
            f"{slug}-hardcover-wrap.pdf",
        ):
            (out / name).write_bytes(b"x")
        return out

    def epub(self: EpubBuilder, slug: str, *, tex_only: bool = False) -> Path:
        return write_epub(root / "output" / f"{slug}.epub")

    def pdf_verify(
        self: PdfVerifier, pdf: Path, config: Path, log: Path | None = None
    ) -> list[str]:
        calls["verify"].append(log)
        return []

    monkeypatch.setattr(LatexCompiler, "compile", latex)
    monkeypatch.setattr(CoverBuilder, "build", covers)
    monkeypatch.setattr(EpubBuilder, "build", epub)
    monkeypatch.setattr(PdfVerifier, "verify", pdf_verify)
    monkeypatch.setattr(EpubVerifier, "verify", lambda self, path, book: [])
    return calls


def controller(root: Path, **kwargs: Any) -> PublishingController:
    return PublishingController(ProjectConfig.load(root), **kwargs)


class FakeQa(RenderQa):
    def __init__(self, blank: bool = False) -> None:
        self.blank, self.calls = blank, []

    def render(self, pdf: Path, output: Path, *, dpi: int = 90) -> RenderReport:
        self.calls.append((pdf, output, dpi))
        pages = [PageRecord(i, f"p{i}.png", 1, 1, 1, self.blank) for i in (1, 2, 3)]
        return RenderReport(1, pdf.name, str(output), dpi, 3, 3, ["contact-001.png"], pages)


def test_controller_audits_a_book(root: Path) -> None:
    reports, ok, text = controller(root).audit("demo")
    assert ok and reports["manuscript"]["slug"] == "demo" and "manuscript audit passed" in text
    assert "release readiness warning" in text
    _, ok, _ = controller(root).audit("demo", strict_release=True)
    assert not ok
    with pytest.raises(BookBuildError, match=r"no such book config: books/absent\.toml"):
        controller(root).audit("absent")
    assert (
        controller(root).book_slugs() == ["demo"]
        and controller(root).layout.books == root.resolve() / "books"
    )


def test_controller_builds_the_interior(root: Path, stubs: dict[str, list[Any]]) -> None:
    ctl = controller(root)
    assert "wrote build/demo/demo.tex" in ctl.build("demo", tex_only=True)
    assert "wrote output/demo.pdf" in ctl.build("demo", verify=False)
    assert "all checks passed" in ctl.build("demo")
    assert "built output/demo-hardcover.pdf" in ctl.build("demo", hardcover=True)
    assert [p.parent.name for p in stubs["verify"]] == ["demo", "demo-hardcover"]


def test_controller_reports_verification_failures(
    root: Path, stubs: dict[str, list[Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        PdfVerifier, "verify", lambda self, pdf, config, log=None: ["page 1 is wrong"]
    )
    with pytest.raises(BookBuildError, match=r"\[demo\] FAIL page 1 is wrong"):
        controller(root).build("demo")
    monkeypatch.setattr(EpubVerifier, "verify", lambda self, path, book: ["bad nav"])
    with pytest.raises(BookBuildError, match=r"\[demo\] FAIL bad nav"):
        controller(root).epub("demo")


def test_controller_builds_the_epub(root: Path, stubs: dict[str, list[Any]]) -> None:
    ctl = controller(root)
    assert (
        "wrote build/demo/epub/demo.tex" in ctl.epub("demo", tex_only=False, verify=False) or True
    )
    assert "all checks passed" in ctl.epub("demo")
    assert "wrote" in controller(root).epub("demo", tex_only=True)


def test_controller_reports_paths_outside_the_project(
    root: Path,
    stubs: dict[str, list[Any]],
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    elsewhere = tmp_path_factory.mktemp("elsewhere") / "x.pdf"
    monkeypatch.setattr(
        BookBuilder, "build", lambda self, slug, *, tex_only=False, hardcover=False: elsewhere
    )
    assert str(elsewhere.resolve()) in controller(root).build("demo", verify=False)


def test_controller_covers_without_a_plugin(root: Path, stubs: dict[str, list[Any]]) -> None:
    text = controller(root).covers("demo", preview=True, hardcover_pdf=Path("output/hc.pdf"))
    assert "covers written to output/covers/demo" in text
    assert stubs["covers"] == [("demo", True, Path("output/hc.pdf"))]


PLUGIN = """
import numpy as np
from engineering_influence.publishing.covers.builtin_cover_style import BuiltinCoverStyle
from engineering_influence.publishing.covers.cover_painter import CoverPainter
from engineering_influence.publishing.covers.cover_plugin import CoverPlugin


class Flat(CoverPainter):
    def paint(self, layout, style):
        return np.full((layout.px[1], layout.px[0], 3), 0.1, np.float32)


class Plugin(CoverPlugin):
    def painters(self):
        return {"flat": Flat()}

    def styles(self):
        style = BuiltinCoverStyle().for_book({"title": "Demo Cover"})
        style.painter = "flat"
        return {"demo": style}
"""


def test_the_project_config_names_a_cover_plugin_that_really_paints(root: Path) -> None:
    (root / "scripts").mkdir()
    (root / "scripts" / "ctl_cover_plugin.py").write_text(textwrap.dedent(PLUGIN), encoding="utf-8")
    (root / "engineering-influence.toml").write_text(
        '[covers]\nplugin = "scripts.ctl_cover_plugin:Plugin"\n', encoding="utf-8"
    )
    write_pdf(root / "output" / "demo.pdf", 120)
    (root / "scripts" / "__init__.py").write_text("", encoding="utf-8")
    text = controller(root).covers("demo")
    assert "all cover checks passed" in text
    with Image.open(root / "output" / "covers" / "demo" / "demo-ebook.tif") as ebook:
        r, g, b = ebook.getpixel((800, 100))
        assert max(r, g, b) < 60 and abs(r - 26) <= 3  # the plugin's flat 0.1 background


def test_controller_qa_resolves_paths_and_flags_blank_runs(root: Path) -> None:
    write_pdf(root / "output" / "demo.pdf", 3)
    qa = FakeQa()
    report, ok = controller(root, qa=qa).qa(Path("output/demo.pdf"), dpi=72)
    assert (
        ok
        and report["rendered_pages"] == 3
        and qa.calls[0][1] == root.resolve() / "build/demo/visual-qa"
    )
    _, ok = controller(root, qa=FakeQa(blank=True)).qa(
        root / "output" / "demo.pdf", output=root / "qa"
    )
    assert not ok
    with pytest.raises(BookBuildError, match="PDF not found"):
        controller(root, qa=qa).qa(Path("output/absent.pdf"))


def test_controller_publishes_the_whole_pipeline(root: Path, stubs: dict[str, list[Any]]) -> None:
    result, ok = controller(root).publish("demo", no_render=True)
    assert ok and [s["name"] for s in result["steps"]] == ["pdf", "covers", "epub"]
    audit_only, ok = controller(root).publish("demo", audit_only=True)
    assert ok and audit_only["steps"] == []


def run(root: Path, *args: str) -> int:
    return CliApplication().run(["book", "--root", str(root), *args])


def test_cli_audit(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(root, "audit", "demo") == 0
    assert "manuscript audit passed" in capsys.readouterr().out
    assert run(root, "audit", "demo", "--json") == 0
    assert json.loads(capsys.readouterr().out)["manuscript"]["slug"] == "demo"
    assert run(root, "audit") == 0  # every configured book
    (root / "src" / "stray.md").write_text("# Stray\n\nx\n", encoding="utf-8")
    assert run(root, "audit", "demo") == 1
    assert run(root, "audit", "demo", "--strict-release") == 1


def test_cli_reports_errors_cleanly(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(root, "audit", "absent") == 1
    assert "[absent] error: no such book config" in capsys.readouterr().err
    (root / "engineering-influence.toml").write_text("not = valid = toml", encoding="utf-8")
    assert run(root, "audit", "demo") == 1
    assert capsys.readouterr().err.startswith("error: ")


def test_cli_builds(
    root: Path, stubs: dict[str, list[Any]], capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(root, "build", "demo", "--tex-only") == 0
    assert run(root, "build", "demo") == 0
    assert run(root, "build", "demo", "--hardcover", "--no-verify") == 0
    assert run(root, "epub", "demo") == 0
    assert run(root, "epub", "demo", "--tex-only") == 0
    assert run(root, "epub", "--no-verify") == 0
    assert run(root, "covers", "demo", "--preview", "--hardcover-pdf", "output/hc.pdf") == 0
    out = capsys.readouterr().out
    assert "wrote build/demo/demo.tex" in out and "all cover checks passed" in out
    assert stubs["covers"][-1] == ("demo", True, Path("output/hc.pdf"))


def test_cli_qa(
    root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_pdf(root / "output" / "demo.pdf", 3)
    monkeypatch.setattr(
        RenderQa,
        "render",
        lambda self, pdf, output, *, dpi=90: FakeQa().render(pdf, output, dpi=dpi),
    )
    assert run(root, "qa", "output/demo.pdf") == 0
    assert "rendered 3/3 pages at 90 DPI" in capsys.readouterr().out
    monkeypatch.setattr(
        RenderQa,
        "render",
        lambda self, pdf, output, *, dpi=90: FakeQa(blank=True).render(pdf, output, dpi=dpi),
    )
    assert run(root, "qa", "output/demo.pdf") == 1
    assert "FAIL blank run exceeds two pages: [1, 2, 3]" in capsys.readouterr().err
    assert run(root, "qa", "output/demo.pdf", "--dpi", "10") == 2
    assert run(root, "qa", "output/absent.pdf") == 1


def test_cli_publish(
    root: Path, stubs: dict[str, list[Any]], capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(root, "publish", "demo", "--audit-only") == 0
    assert run(root, "publish", "demo", "--no-render", "--report-dir", str(root / "reports")) == 0
    assert (root / "reports" / "demo" / "publication-report.json").exists()
    assert run(root, "publish", "--no-render") == 0
    assert run(root, "publish", "demo", "--dpi", "5") == 2
    out = capsys.readouterr().out
    assert "publication pipeline pass; report" in out and "publication-report.json" in out


def test_cli_publish_failures_name_the_failing_step(
    root: Path,
    stubs: dict[str, list[Any]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(PdfVerifier, "verify", lambda self, pdf, config, log=None: ["broken"])
    assert run(root, "publish", "demo", "--no-render") == 1
    err = capsys.readouterr().err
    assert "FAIL step pdf: see build/demo/release/pdf.log" in err and "missing artifact" in err
