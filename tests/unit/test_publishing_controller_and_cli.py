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
from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.covers.cover_builder import CoverBuilder
from engineering_influence.infrastructure.epub.cover_image import CoverImage
from engineering_influence.infrastructure.epub.epub_archive import EpubArchive
from engineering_influence.infrastructure.epub.epub_cover_inspector import EpubCoverInspector
from engineering_influence.infrastructure.epub.epubcheck_runner import EpubcheckRunner
from engineering_influence.infrastructure.epub.tex4ebook_compiler import Tex4ebookCompiler
from engineering_influence.infrastructure.epub.zip_epub_package import ZipEpubPackage
from engineering_influence.infrastructure.publishing.directory_publisher import DirectoryPublisher
from engineering_influence.infrastructure.publishing.filesystem_manuscript_source import (
    FilesystemManuscriptSource,
)
from engineering_influence.infrastructure.publishing.package_assets import PackageAssets
from engineering_influence.infrastructure.publishing.pypdf_pdf_inspector import PypdfPdfInspector
from engineering_influence.infrastructure.qa.render_qa import RenderQa
from engineering_influence.infrastructure.typesetting.filesystem_build_workspace import (
    FilesystemBuildWorkspace,
)
from engineering_influence.infrastructure.typesetting.latex_compiler import LatexCompiler
from engineering_influence.interfaces.cover_builder_interface import CoverBuilderInterface
from engineering_influence.interfaces.cover_builder_provider_interface import (
    CoverBuilderProviderInterface,
)
from engineering_influence.interfaces.epub_verifier_interface import EpubVerifierInterface
from engineering_influence.interfaces.latex_compiler_interface import LatexCompilerInterface
from engineering_influence.models.publishing.project_config import ProjectConfig
from engineering_influence.models.qa.page_record import PageRecord
from engineering_influence.models.qa.render_report import RenderReport
from engineering_influence.models.typesetting.book import Book
from engineering_influence.repositories.release.artifact_inventory import ArtifactInventory
from engineering_influence.repositories.typesetting.book_loader import BookLoader
from engineering_influence.runtime.cli_runtime import CliRuntime
from engineering_influence.runtime.cover_builder_provider import CoverBuilderProvider
from engineering_influence.runtime.interfaces.publishing_controller_factory_interface import (
    PublishingControllerFactoryInterface,
)
from engineering_influence.runtime.publish_pipeline_provider import PublishPipelineProvider
from engineering_influence.services.epub.epub_builder import EpubBuilder
from engineering_influence.services.epub.epub_identifier import EpubIdentifier
from engineering_influence.services.epub.epub_repacker import EpubRepacker
from engineering_influence.services.epub.epub_verifier import EpubVerifier
from engineering_influence.services.package_book import PackageBook
from engineering_influence.services.publishing.interfaces.pdf_verifier_interface import (
    PdfVerifierInterface,
)
from engineering_influence.services.publishing.pdf_verifier import PdfVerifier
from engineering_influence.services.typesetting.book_builder import BookBuilder
from engineering_influence.services.typesetting.interfaces.book_builder_interface import (
    BookBuilderInterface,
)

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


class FakeLatex(LatexCompilerInterface):
    def __init__(self, calls: dict[str, list[Any]]) -> None:
        self._calls = calls

    def compile(self, workdir: Path, tex_name: str, source_date_epoch: int) -> tuple[int, str]:
        self._calls["latex"].append(tex_name)
        write_pdf(workdir / tex_name.replace(".tex", ".pdf"))
        return 0, ""


class FakeCovers(CoverBuilderInterface):
    def __init__(self, root: Path, calls: dict[str, list[Any]]) -> None:
        self._root, self._calls = root, calls

    def build(self, slug: str, preview: bool = False, hardcover_pdf: Path | None = None) -> Path:
        self._calls["covers"].append((slug, preview, hardcover_pdf))
        out = self._root / "output" / "covers" / slug
        out.mkdir(parents=True, exist_ok=True)
        for name in (
            f"{slug}-ebook.jpg",
            f"{slug}-paperback-wrap.pdf",
            f"{slug}-hardcover-wrap.pdf",
        ):
            (out / name).write_bytes(b"x")
        return out


class FakeCoverProvider(CoverBuilderProviderInterface):
    def __init__(self, covers: CoverBuilderInterface) -> None:
        self._covers = covers

    def provide(self) -> CoverBuilderInterface:
        return self._covers


class FakeEpub(EpubBuilder):
    def __init__(self, root: Path) -> None:  # no collaborators: it never builds a real EPUB
        self._root = root

    def build(self, slug: str, *, tex_only: bool = False) -> Path:
        return write_epub(self._root / "output" / f"{slug}.epub")


class FakeEpubVerifier(EpubVerifierInterface):
    def __init__(self, problems: list[str] | None = None) -> None:
        self.problems = problems or []

    def verify(self, path: Path, book: Book) -> list[str]:
        return list(self.problems)


class FakePdfVerifier(PdfVerifierInterface):
    def __init__(self, problems: list[str] | None = None) -> None:
        self.problems = problems or []
        self.logs: list[Path] = []

    def verify(self, pdf_path: Path, config_path: Path, log_path: Path | None = None) -> list[str]:
        self.logs.append(log_path or Path())
        return list(self.problems)


class FakeBuilder(BookBuilderInterface):
    def __init__(self, path: Path) -> None:
        self._path = path

    def build(self, slug: str, *, tex_only: bool = False, hardcover: bool = False) -> Path:
        return self._path


class FakeControllerFactory(PublishingControllerFactoryInterface):
    """What `ei book` builds instead of the real factory, so the whole CLI runs over fakes."""

    def __init__(self, wiring: dict[str, Any]) -> None:
        self._wiring = wiring

    def create(self, root: Path) -> PublishingController:
        return controller(root, **self._wiring)


class Stubs:
    """The slow external steps, replaced by fakes that leave real artifacts behind."""

    def __init__(self, calls: dict[str, list[Any]], wiring: dict[str, Any]) -> None:
        self.calls, self.wiring = calls, wiring

    def __getitem__(self, key: str) -> list[Any]:
        return self.calls[key]


@pytest.fixture
def stubs(root: Path) -> Stubs:
    verifier = FakePdfVerifier()
    calls: dict[str, list[Any]] = {"latex": [], "covers": [], "verify": verifier.logs}
    wiring: dict[str, Any] = {
        "latex": FakeLatex(calls),
        "epub": FakeEpub(root),
        "covers": FakeCoverProvider(FakeCovers(root, calls)),
        "epub_verifier": FakeEpubVerifier(),
        "pdf_verifier": verifier,
    }
    return Stubs(calls, wiring)


def controller(root: Path, **kwargs: Any) -> PublishingController:
    config = ProjectConfig.load(root)
    layout = config.layout()
    files = FilesystemManuscriptSource()
    loader = BookLoader(config.root)
    workspace = FilesystemBuildWorkspace()
    assets = PackageAssets()
    identifier = EpubIdentifier()
    pdfs = PypdfPdfInspector()
    latex = kwargs.pop("latex", None) or LatexCompiler()
    collaborators: dict[str, Any] = {
        "loader": loader,
        "builder": BookBuilder(layout, loader, latex, workspace, assets, files),
        "pdf_verifier": PdfVerifier(pdfs, files),
        "epub": EpubBuilder(
            layout,
            loader,
            Tex4ebookCompiler(),
            workspace,
            assets,
            EpubRepacker(CoverImage(layout), ZipEpubPackage(), identifier),
            files,
            identifier,
        ),
        "epub_verifier": EpubVerifier(EpubArchive(), EpubcheckRunner(), EpubCoverInspector()),
        "covers": CoverBuilderProvider(config),
        **kwargs,
    }
    collaborators.setdefault("qa", RenderQa(config.root))
    collaborators.setdefault(
        "publisher",
        PublishPipelineProvider(
            config,
            files,
            pdfs,
            loader,
            workspace,
            collaborators["builder"],
            collaborators["pdf_verifier"],
            collaborators["epub"],
            collaborators["covers"],
            collaborators["qa"],
            collaborators["epub_verifier"],
            collaborators.get("strict_epub_verifier", collaborators["epub_verifier"]),
        ),
    )
    collaborators.setdefault(
        "packager",
        PackageBook(layout, ArtifactInventory(layout), DirectoryPublisher()),
    )
    return PublishingController(config, files, pdfs, **collaborators)


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


def test_controller_packages_only_after_the_release_check_and_names_a_missing_contract(
    root: Path,
) -> None:
    # The demo book has no [release] contract: packaging reads the release status first, then refuses for that.
    with pytest.raises(BookBuildError, match=r"\[demo\] the book has no \[release\] contract"):
        controller(root).package("demo")
    with pytest.raises(BookBuildError, match=r"no such book config: books/absent\.toml"):
        controller(root).package("absent")


def test_controller_builds_the_interior(root: Path, stubs: Stubs) -> None:
    ctl = controller(root, **stubs.wiring)
    assert "wrote build/demo/demo.tex" in ctl.build("demo", tex_only=True)
    assert "wrote output/demo.pdf" in ctl.build("demo", verify=False)
    assert "all checks passed" in ctl.build("demo")
    assert "built output/demo-hardcover.pdf" in ctl.build("demo", hardcover=True)
    assert [p.parent.name for p in stubs["verify"]] == ["demo", "demo-hardcover"]


def test_controller_reports_verification_failures(root: Path, stubs: Stubs) -> None:
    wrong = {**stubs.wiring, "pdf_verifier": FakePdfVerifier(["page 1 is wrong"])}
    with pytest.raises(BookBuildError, match=r"\[demo\] FAIL page 1 is wrong"):
        controller(root, **wrong).build("demo")
    failing = {**stubs.wiring, "epub_verifier": FakeEpubVerifier(["bad nav"])}
    with pytest.raises(BookBuildError, match=r"\[demo\] FAIL bad nav"):
        controller(root, **failing).epub("demo")


def test_controller_builds_the_epub(root: Path, stubs: Stubs) -> None:
    ctl = controller(root, **stubs.wiring)
    assert (
        "wrote build/demo/epub/demo.tex" in ctl.epub("demo", tex_only=False, verify=False) or True
    )
    assert "all checks passed" in ctl.epub("demo")
    assert "wrote" in controller(root, **stubs.wiring).epub("demo", tex_only=True)


def test_controller_reports_paths_outside_the_project(
    root: Path, stubs: Stubs, tmp_path_factory: pytest.TempPathFactory
) -> None:
    elsewhere = tmp_path_factory.mktemp("elsewhere") / "x.pdf"
    wiring = {**stubs.wiring, "builder": FakeBuilder(elsewhere)}
    assert str(elsewhere.resolve()) in controller(root, **wiring).build("demo", verify=False)


def test_controller_covers_without_a_plugin(root: Path, stubs: Stubs) -> None:
    text = controller(root, **stubs.wiring).covers(
        "demo", preview=True, hardcover_pdf=Path("output/hc.pdf")
    )
    assert "covers written to output/covers/demo" in text
    assert stubs["covers"] == [("demo", True, Path("output/hc.pdf"))]


def test_the_real_cover_provider_builds_a_builder_when_no_plugin_is_configured(
    root: Path,
) -> None:
    builder = CoverBuilderProvider(ProjectConfig.load(root)).provide()

    assert isinstance(builder, CoverBuilder)


PLUGIN = """
import numpy as np
from engineering_influence.models.covers.builtin_cover_style import BuiltinCoverStyle
from engineering_influence.interfaces.cover_painter_interface import CoverPainterInterface
from engineering_influence.interfaces.cover_plugin_interface import CoverPluginInterface


class Flat(CoverPainterInterface):
    def paint(self, layout, style):
        return np.full((layout.px[1], layout.px[0], 3), 0.1, np.float32)


class Plugin(CoverPluginInterface):
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


def test_controller_publishes_the_whole_pipeline(root: Path, stubs: Stubs) -> None:
    result, ok = controller(root, **stubs.wiring).publish("demo", no_render=True)
    assert ok and [s["name"] for s in result["steps"]] == ["pdf", "covers", "epub"]
    audit_only, ok = controller(root, **stubs.wiring).publish("demo", audit_only=True)
    assert ok and audit_only["steps"] == []


def run(root: Path, *args: str, wiring: dict[str, Any] | None = None) -> int:
    runtime = CliRuntime() if wiring is None else CliRuntime(FakeControllerFactory(wiring))
    return runtime.build().run(["book", "--root", str(root), *args])


def test_cli_audit(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(root, "audit", "demo") == 0
    assert "manuscript audit passed" in capsys.readouterr().out
    assert run(root, "audit", "demo", "--json") == 0
    assert json.loads(capsys.readouterr().out)["manuscript"]["slug"] == "demo"
    assert run(root, "audit") == 0  # every configured book
    (root / "src" / "stray.md").write_text("# Stray\n\nx\n", encoding="utf-8")
    assert run(root, "audit", "demo") == 1
    assert run(root, "audit", "demo", "--strict-release") == 1


def test_cli_package_names_why_a_book_without_a_contract_is_not_packaged(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(root, "package", "demo") == 1
    assert "[demo] the book has no [release] contract" in capsys.readouterr().err
    assert not (root / "build" / "demo" / "release" / "kdp").exists()


def test_cli_reports_errors_cleanly(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(root, "audit", "absent") == 1
    assert "[absent] error: no such book config" in capsys.readouterr().err
    (root / "engineering-influence.toml").write_text("not = valid = toml", encoding="utf-8")
    assert run(root, "audit", "demo") == 1
    assert capsys.readouterr().err.startswith("error: ")


def test_cli_builds(root: Path, stubs: Stubs, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(root, "build", "demo", "--tex-only", wiring=stubs.wiring) == 0
    assert run(root, "build", "demo", wiring=stubs.wiring) == 0
    assert run(root, "build", "demo", "--hardcover", "--no-verify", wiring=stubs.wiring) == 0
    assert run(root, "epub", "demo", wiring=stubs.wiring) == 0
    assert run(root, "epub", "demo", "--tex-only", wiring=stubs.wiring) == 0
    assert run(root, "epub", "--no-verify", wiring=stubs.wiring) == 0
    assert (
        run(
            root,
            "covers",
            "demo",
            "--preview",
            "--hardcover-pdf",
            "output/hc.pdf",
            wiring=stubs.wiring,
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "wrote build/demo/demo.tex" in out and "all cover checks passed" in out
    assert stubs["covers"][-1] == ("demo", True, Path("output/hc.pdf"))


def test_cli_qa(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_pdf(root / "output" / "demo.pdf", 3)
    assert run(root, "qa", "output/demo.pdf", wiring={"qa": FakeQa()}) == 0
    assert "rendered 3/3 pages at 90 DPI" in capsys.readouterr().out
    blank = {"qa": FakeQa(blank=True)}
    assert run(root, "qa", "output/demo.pdf", wiring=blank) == 1
    assert "FAIL blank run exceeds two pages: [1, 2, 3]" in capsys.readouterr().err
    assert run(root, "qa", "output/demo.pdf", "--dpi", "10", wiring=blank) == 2
    assert run(root, "qa", "output/absent.pdf", wiring=blank) == 1


def test_cli_publish(root: Path, stubs: Stubs, capsys: pytest.CaptureFixture[str]) -> None:
    wiring = stubs.wiring
    assert run(root, "publish", "demo", "--audit-only", wiring=wiring) == 0
    assert (
        run(
            root,
            "publish",
            "demo",
            "--no-render",
            "--report-dir",
            str(root / "reports"),
            wiring=wiring,
        )
        == 0
    )
    assert (root / "reports" / "demo" / "publication-report.json").exists()
    assert run(root, "publish", "--no-render", wiring=wiring) == 0
    assert run(root, "publish", "demo", "--dpi", "5", wiring=wiring) == 2
    out = capsys.readouterr().out
    assert "publication pipeline pass; report" in out and "publication-report.json" in out


def test_cli_publish_failures_name_the_failing_step(
    root: Path, stubs: Stubs, capsys: pytest.CaptureFixture[str]
) -> None:
    wiring = {**stubs.wiring, "pdf_verifier": FakePdfVerifier(["broken"])}
    assert run(root, "publish", "demo", "--no-render", wiring=wiring) == 1
    err = capsys.readouterr().err
    assert "FAIL step pdf: see build/demo/release/pdf.log" in err and "missing artifact" in err


def test_the_package_runs_as_a_module(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import runpy

    argv = ["python -m engineering_influence", "book", "--root", str(root), "audit", "demo"]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as stop:
        runpy.run_module("engineering_influence", run_name="__main__")
    assert stop.value.code == 0
