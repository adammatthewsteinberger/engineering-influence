"""Visual QA: blank detection, reports, rasterizer, contact sheets, and the render service."""

import os
import stat
import sys
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfWriter

from engineering_influence.publishing.path_relativizer import PathRelativizer
from engineering_influence.publishing.qa.blank_page_detector import BlankPageDetector
from engineering_influence.publishing.qa.contact_sheet_builder import ContactSheetBuilder
from engineering_influence.publishing.qa.page_file_number import PageFileNumber
from engineering_influence.publishing.qa.page_rasterizer import PageRasterizer
from engineering_influence.publishing.qa.page_record import PageRecord
from engineering_influence.publishing.qa.render_qa import RenderQa
from engineering_influence.publishing.qa.render_report import RenderReport
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError


def record(page: int, blank: bool) -> PageRecord:
    return PageRecord(page, f"p{page}.png", 10, 10, 1, blank)


def test_page_numbers_come_from_file_names() -> None:
    number = PageFileNumber()
    assert number.of(Path("render-0012.png")) == 12
    assert number.of(Path("page-0003.png")) == 3
    assert number.of(Path("notes.png")) == 0 and number.of(Path("a1.txt")) == 0


def test_blank_detection() -> None:
    detector = BlankPageDetector()
    assert detector.is_blank(Image.new("RGB", (100, 150), "white"))
    assert detector.is_blank(Image.new("RGB", (100, 150), (250, 250, 250)))
    marked = Image.new("RGB", (100, 150), "white")
    marked.putpixel((5, 5), (0, 0, 0))
    assert not detector.is_blank(marked)
    assert not detector.is_blank(Image.new("L", (10, 10), 100))


def test_report_lists_blank_pages_and_only_runs_longer_than_two() -> None:
    pages = [record(1, False), record(2, True), record(3, True), record(4, False)]
    pages += [record(5, True), record(6, True), record(7, True), record(8, False), record(9, True)]
    report = RenderReport(1, "a.pdf", "out", 90, 9, 9, [], pages)
    assert report.blank_pages == [2, 3, 5, 6, 7, 9]
    assert report.unexpected_blank_pages == [5, 6, 7]
    as_dict = report.as_dict()
    assert as_dict["unexpected_blank_pages"] == [5, 6, 7] and as_dict["pages"][0]["page"] == 1


def test_a_trailing_blank_run_is_counted() -> None:
    report = RenderReport(
        1, "a.pdf", "o", 90, 3, 3, [], [record(1, True), record(2, True), record(3, True)]
    )
    assert report.unexpected_blank_pages == [1, 2, 3]


def fake_renderer(
    directory: Path, name: str, pages_to_write: int | None = None, fail: bool = False
) -> None:
    """A stand-in renderer script that writes numbered PNGs like pdftoppm or mutool draw."""
    directory.mkdir(exist_ok=True)
    body = f"""#!{sys.executable}
import sys
from PIL import Image
args = sys.argv[1:]
if {fail!r}:
    print("boom", file=sys.stderr); sys.exit(3)
n = {pages_to_write!r} if {pages_to_write!r} is not None else None
if "{name}" == "pdftoppm":
    last = int(args[args.index("-l") + 1]); prefix = args[-1]
    count = n if n is not None else last
    for i in range(1, count + 1):
        Image.new("RGB", (60, 90), "white" if i == 2 else (10, 10, 10)).save(f"{{prefix}}-{{i:03d}}.png")
else:
    pattern = args[args.index("-o") + 1]
    count = n if n is not None else 3
    for i in range(1, count + 1):
        Image.new("RGB", (60, 90), "white" if i == 2 else (10, 10, 10)).save(pattern.replace("%04d", f"{{i:04d}}"))
"""
    path = directory / name
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def pdf_of(path: Path, pages: int = 3) -> Path:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(432, 648)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def only_path(monkeypatch: pytest.MonkeyPatch, directory: Path) -> None:
    monkeypatch.setenv("PATH", str(directory))


def test_rasterizer_needs_a_renderer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    only_path(monkeypatch, tmp_path)
    with pytest.raises(BookBuildError, match="needs pdftoppm"):
        PageRasterizer().command()


def test_rasterizer_prefers_pdftoppm_and_renumbers_pages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_renderer(tmp_path / "bin", "pdftoppm")
    fake_renderer(tmp_path / "bin", "mutool")
    only_path(monkeypatch, tmp_path / "bin")
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "page-9999.png").write_bytes(b"stale")
    (pages / "keep.txt").write_text("keep")
    assert PageRasterizer().command() == "pdftoppm"
    PageRasterizer().rasterize(pdf_of(tmp_path / "a.pdf"), pages, 90, 3)
    assert sorted(p.name for p in pages.iterdir()) == [
        "keep.txt",
        "page-0001.png",
        "page-0002.png",
        "page-0003.png",
    ]


def test_rasterizer_falls_back_to_mutool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_renderer(tmp_path / "bin", "mutool")
    only_path(monkeypatch, tmp_path / "bin")
    assert PageRasterizer().command() == "mutool"
    PageRasterizer().rasterize(pdf_of(tmp_path / "a.pdf"), tmp_path / "pages", 72, 3)
    assert (tmp_path / "pages" / "page-0003.png").exists()


def test_rasterizer_reports_renderer_failures_and_missing_pages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_renderer(tmp_path / "fail", "pdftoppm", fail=True)
    only_path(monkeypatch, tmp_path / "fail")
    with pytest.raises(BookBuildError, match="PDF renderer failed:\nboom"):
        PageRasterizer().rasterize(pdf_of(tmp_path / "a.pdf"), tmp_path / "p1", 90, 3)
    fake_renderer(tmp_path / "short", "pdftoppm", pages_to_write=2)
    only_path(monkeypatch, tmp_path / "short")
    with pytest.raises(BookBuildError, match="renderer produced 2 pages; PDF has 3"):
        PageRasterizer().rasterize(pdf_of(tmp_path / "a.pdf"), tmp_path / "p2", 90, 3)


def make_pages(directory: Path, count: int) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(1, count + 1):
        path = directory / f"page-{i:04d}.png"
        Image.new("RGB", (60, 90), (i * 5 % 255, 40, 40)).save(path)
        paths.append(path)
    return paths


def test_contact_sheets_hold_sixteen_pages_each(tmp_path: Path) -> None:
    builder = ContactSheetBuilder(PathRelativizer(tmp_path))
    pages = make_pages(tmp_path / "pages", 17)
    sheets = builder.build(pages, tmp_path)
    assert sheets == ["contact-001.png", "contact-002.png"]
    with (
        Image.open(tmp_path / "contact-001.png") as first,
        Image.open(tmp_path / "contact-002.png") as second,
    ):
        assert first.size == second.size
    assert builder.build([], tmp_path) == []


def test_contact_sheets_report_outside_paths_absolutely(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    builder = ContactSheetBuilder(PathRelativizer(root))
    out = tmp_path / "elsewhere"
    out.mkdir()
    sheets = builder.build(make_pages(tmp_path / "pages", 2), out)
    assert sheets == [str((out / "contact-001.png").resolve())]


def test_clearing_removes_only_contact_sheets(tmp_path: Path) -> None:
    builder = ContactSheetBuilder(PathRelativizer(tmp_path))
    builder.clear(tmp_path / "absent")
    (tmp_path / "contact-007.png").write_bytes(b"x")
    (tmp_path / "other.png").write_bytes(b"x")
    builder.clear(tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["other.png"]


def test_render_qa_produces_pages_records_and_sheets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_renderer(tmp_path / "bin", "pdftoppm")
    only_path(monkeypatch, tmp_path / "bin")
    root = tmp_path / "proj"
    root.mkdir()
    pdf = pdf_of(root / "book.pdf")
    stale = root / "qa"
    stale.mkdir()
    (stale / "contact-099.png").write_bytes(b"old")
    report = RenderQa(root).render(pdf, stale, dpi=72)
    assert (report.page_count, report.rendered_pages, report.dpi) == (3, 3, 72)
    assert report.pdf == "book.pdf" and report.output == "qa"
    assert [p.blank for p in report.pages] == [False, True, False]
    assert report.pages[0].path == "qa/pages/page-0001.png" and report.pages[0].width == 60
    assert (
        report.contact_sheets == ["qa/contact-001.png"] and not (stale / "contact-099.png").exists()
    )
    assert report.unexpected_blank_pages == []


def test_render_qa_defaults_to_the_real_rasterizer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    only_path(monkeypatch, tmp_path)
    pdf = pdf_of(tmp_path / "book.pdf")
    with pytest.raises(BookBuildError, match="needs pdftoppm"):
        RenderQa(tmp_path).render(pdf, tmp_path / "qa")
    assert os.environ["PATH"] == str(tmp_path)


def test_clearing_pages_tolerates_a_missing_directory(tmp_path: Path) -> None:
    PageRasterizer().clear_pages(tmp_path / "absent")
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "render-0001.png").write_bytes(b"x")
    (pages / "page-0001.png").write_bytes(b"x")
    (pages / "notes.txt").write_text("keep")
    PageRasterizer().clear_pages(pages)
    assert [p.name for p in pages.iterdir()] == ["notes.txt"]
