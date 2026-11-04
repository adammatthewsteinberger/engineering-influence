"""Repacker, tex4ebook runner, builder, and epubcheck runner."""

import os
import stat
import zipfile
from pathlib import Path

import pytest
from conftest import raw_epub

from engineering_influence.publishing.epub.cover_image import CoverImage
from engineering_influence.publishing.epub.epub_builder import EpubBuilder
from engineering_influence.publishing.epub.epub_repacker import EpubRepacker
from engineering_influence.publishing.epub.epub_verifier import EpubVerifier
from engineering_influence.publishing.epub.epubcheck_runner import EpubcheckRunner
from engineering_influence.publishing.epub.tex4ebook_compiler import Tex4ebookCompiler
from engineering_influence.publishing.project_layout import ProjectLayout
from engineering_influence.publishing.typesetting.book import Book
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError


def test_repacked_epub_is_finished_deterministic_and_valid(finished: Path, book: Book) -> None:
    with zipfile.ZipFile(finished) as z:
        infos = z.infolist()
        assert infos[0].filename == "mimetype" and infos[0].compress_type == zipfile.ZIP_STORED
        assert {i.date_time for i in infos} == {(2031, 1, 1, 0, 0, 0)}
        names = z.namelist()
        assert "OEBPS/nav.xhtml" in names and "OEBPS/cover.jpg" in names
        opf = z.read("OEBPS/demo.opf").decode()
        toc = z.read("OEBPS/toc.xhtml").decode()
        css = z.read("OEBPS/demo.css").decode()
        chapter = z.read("OEBPS/c1.xhtml").decode()
    assert "<dc:date>2031</dc:date>" in opf and ">2031-01-01T00:00:00Z</meta>" in opf
    assert 'properties="nav"></item>' in opf and 'href="toc.xhtml" id="toc"' in opf
    assert '<div class="toc">' in toc and "<nav" not in toc
    assert "display" not in css and "margin: 0" in css
    assert "<h2 class='chapterHead' id='h3'>One</h2>" in chapter and "xml:lang" in chapter
    assert EpubVerifier().verify(finished, book) == []


def test_repack_is_reproducible(
    tmp_path: Path, raw: Path, book: Book, layout: ProjectLayout
) -> None:
    first, second = tmp_path / "a.epub", tmp_path / "b.epub"
    EpubRepacker(CoverImage(layout)).repack(raw, book, first)
    EpubRepacker(CoverImage(layout)).repack(raw, book, second)
    assert first.read_bytes() == second.read_bytes()


def test_repack_rejects_a_package_without_navigation(
    tmp_path: Path, book: Book, layout: ProjectLayout
) -> None:
    raw = raw_epub(tmp_path / "raw.epub")
    with zipfile.ZipFile(raw) as z:
        members = {n: z.read(n) for n in z.namelist()}
    members["OEBPS/demo.opf"] = members["OEBPS/demo.opf"].replace(b'properties="nav"', b"")
    broken = tmp_path / "broken.epub"
    with zipfile.ZipFile(broken, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    with pytest.raises(ValueError, match="no navigation document or NCX"):
        EpubRepacker(CoverImage(layout)).repack(broken, book, tmp_path / "out.epub")


def fake_tool(directory: Path, name: str, script: str) -> None:
    directory.mkdir(exist_ok=True)
    path = directory / name
    path.write_text("#!/bin/sh\n" + script, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_tex4ebook_compiler_runs_the_epub3_conversion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_tool(tmp_path / "bin", "tex4ebook", 'echo "out:$*"\necho "err" >&2\nexit 2\n')
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")
    status, output = Tex4ebookCompiler().compile(tmp_path, "b.tex")
    assert status == 2 and "out:-l -f epub3 -c fine-ebook.cfg b.tex" in output and "err" in output


class FakeTex4ebook(Tex4ebookCompiler):
    def __init__(self, status: int = 0, write_epub: bool = True, write_log: bool = False) -> None:
        self.status, self.write_epub, self.write_log = status, write_epub, write_log
        self.calls: list[tuple[Path, str]] = []

    def compile(self, workdir: Path, tex_name: str) -> tuple[int, str]:
        self.calls.append((workdir, tex_name))
        if self.write_epub:
            raw_epub(workdir / "demo.epub")
        if self.write_log:
            (workdir / "demo.log").write_text("EPUB LOG", encoding="utf-8")
        return self.status, "EPUB STDOUT"


def project(root: Path) -> ProjectLayout:
    src = root / "src"
    src.mkdir(exist_ok=True)
    for name, title in (
        ("foreword", "Foreword"),
        ("one", "Chapter 1: One"),
        ("two", "Chapter 2: Two"),
        ("notes", "Notes"),
    ):
        (src / f"{name}.md").write_text(f"# {title}\n\nText begins here.\n", encoding="utf-8")
    (root / "books").mkdir(exist_ok=True)
    (root / "books" / "demo.toml").write_text(
        'source = "src"\ntitle = "Demo Book"\nauthor = "A"\npublisher = "P"\n'
        'edition = "First Edition"\nauthor_bio = "Bio."\nyear = 2031\n'
        'front = ["foreword.md"]\nback = ["notes.md"]\n'
        'parts = [{ title = "The Start", chapters = ["one.md", "two.md"] }]\n',
        encoding="utf-8",
    )
    return ProjectLayout(root)


def test_epub_builder_writes_ebook_sources_without_converting(tmp_path: Path) -> None:
    layout = project(tmp_path)
    compiler = FakeTex4ebook()
    tex = EpubBuilder(layout, compiler=compiler).build("demo", tex_only=True)
    workdir = tex.parent
    assert workdir == tmp_path / "build" / "demo" / "epub" and compiler.calls == []
    assert {"fine-ebook.sty", "fine-ebook.cfg", "fine-ebook.css", "ebook-meta.tex"} <= {
        p.name for p in workdir.iterdir()
    }
    assert "\\usepackage{fine-ebook}" in tex.read_text(encoding="utf-8")


def test_epub_builder_converts_repacks_and_replaces_old_work(
    tmp_path: Path, layout: ProjectLayout
) -> None:
    project(layout.root)
    stale = layout.build / "demo" / "epub" / "stale.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("old")
    epub = EpubBuilder(layout, compiler=FakeTex4ebook()).build("demo")
    assert epub == layout.output / "demo.epub" and not stale.exists()
    with zipfile.ZipFile(epub) as z:
        assert "OEBPS/nav.xhtml" in z.namelist()


def test_epub_builder_reports_conversion_failures(layout: ProjectLayout) -> None:
    project(layout.root)
    with pytest.raises(BookBuildError, match="tex4ebook failed:\nEPUB LOG"):
        EpubBuilder(layout, compiler=FakeTex4ebook(status=1, write_log=True)).build("demo")
    with pytest.raises(BookBuildError, match="tex4ebook failed:\nEPUB STDOUT"):
        EpubBuilder(layout, compiler=FakeTex4ebook(write_epub=False)).build("demo")


@pytest.mark.parametrize("slug", ["../x", "-v", "a b", ""])
def test_epub_builder_rejects_unsafe_slugs_and_unknown_books(
    layout: ProjectLayout, slug: str
) -> None:
    project(layout.root)
    with pytest.raises(BookBuildError, match="invalid book slug"):
        EpubBuilder(layout, compiler=FakeTex4ebook()).build(slug)
    with pytest.raises(BookBuildError, match="no such book config"):
        EpubBuilder(layout, compiler=FakeTex4ebook()).build("absent")


def test_epub_builder_accepts_explicit_assets_and_a_real_default_compiler(tmp_path: Path) -> None:
    layout = project(tmp_path)
    assets = tmp_path / "assets"
    assets.mkdir()
    for name in ("fine-ebook.sty", "fine-ebook.cfg", "fine-ebook.css"):
        (assets / name).write_text(name, encoding="utf-8")
    tex = EpubBuilder(layout, assets).build("demo", tex_only=True)
    assert (tex.parent / "fine-ebook.css").read_text(encoding="utf-8") == "fine-ebook.css"


def test_epubcheck_is_skipped_when_not_installed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    assert EpubcheckRunner().command() is None
    assert EpubcheckRunner().run(tmp_path / "x.epub") == []


def test_epubcheck_bare_executable_reports_findings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    body = 'echo "Picked up JAVA_TOOL_OPTIONS: x"\nfor i in $(seq 1 30); do echo "ERROR $i"; done\nexit 1\n'
    fake_tool(tmp_path / "bin", "epubcheck", body)
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")
    findings = EpubcheckRunner().run(tmp_path / "x.epub")
    assert len(findings) == 20 and findings[0] == "epubcheck: ERROR 1"


def test_epubcheck_success_has_no_findings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_tool(tmp_path / "bin", "epubcheck", "exit 0\n")
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")
    assert EpubcheckRunner().run(tmp_path / "x.epub") == []


def test_epubcheck_jar_needs_java(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    jar = bin_dir / "epubcheck.jar"
    jar.write_text("jar")
    jar.chmod(0o755)
    (bin_dir / "epubcheck").symlink_to(jar)
    monkeypatch.setenv("PATH", str(bin_dir))
    assert EpubcheckRunner().command() is None  # no java on this PATH
    fake_tool(bin_dir, "java", "exit 0\n")
    command = EpubcheckRunner().command()
    assert command is not None and command[:2] == ["java", "-jar"]
    assert command[2].endswith("epubcheck.jar")
