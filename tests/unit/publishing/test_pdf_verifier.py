"""End-to-end verification of a small generated interior."""

from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.infrastructure.publishing.filesystem_manuscript_source import (
    FilesystemManuscriptSource,
)
from engineering_influence.infrastructure.publishing.pypdf_pdf_inspector import PypdfPdfInspector
from engineering_influence.services.publishing.pdf_verifier import PdfVerifier

CONFIG = 'title = "Test Book"\nedition = "First Edition"\n'


def make_pdf(
    path: Path,
    pages: list[list[tuple[float, float, str]]],
    size: tuple[float, float] = (432, 648),
) -> None:
    pdf = canvas.Canvas(str(path), pagesize=size)
    for page in pages:
        for x, y, text in page:
            pdf.drawString(x, y, text)
        pdf.showPage()
    pdf.save()


def book(path: Path) -> None:
    make_pdf(
        path,
        [
            [(100, 560, "Contents"), (100, 540, "Chapter One 1"), (100, 520, "Chapter Two 2")],
            [(200, 612, "1"), (100, 500, "Chapter One"), (100, 480, "Lorem ipsum dolor")],
            [(200, 612, "2"), (100, 500, "Chapter Two"), (100, 480, "Lorem ipsum dolor")],
            [(100, 500, "Copyright First Edition")],
        ],
    )


def test_clean_book_passes(tmp_path: Path) -> None:
    (tmp_path / "b.toml").write_text(CONFIG, encoding="utf-8")
    book(tmp_path / "b.pdf")
    assert (
        PdfVerifier(PypdfPdfInspector(), FilesystemManuscriptSource()).verify(
            tmp_path / "b.pdf", tmp_path / "b.toml"
        )
        == []
    )


def test_log_problems_are_included_when_log_exists(tmp_path: Path) -> None:
    (tmp_path / "b.toml").write_text(CONFIG, encoding="utf-8")
    book(tmp_path / "b.pdf")
    log = tmp_path / "b.log"
    log.write_text("Overfull \\hbox (9.0pt too wide)", encoding="utf-8")
    problems = PdfVerifier(PypdfPdfInspector(), FilesystemManuscriptSource()).verify(
        tmp_path / "b.pdf", tmp_path / "b.toml", log
    )
    assert problems == ["1 overfull lines (worst 9.0pt)"]
    missing = tmp_path / "absent.log"
    assert (
        PdfVerifier(PypdfPdfInspector(), FilesystemManuscriptSource()).verify(
            tmp_path / "b.pdf", tmp_path / "b.toml", missing
        )
        == []
    )


def test_book_without_contents_stops_before_the_log(tmp_path: Path) -> None:
    (tmp_path / "b.toml").write_text(CONFIG, encoding="utf-8")
    make_pdf(tmp_path / "b.pdf", [[(100, 500, "First Edition")]])
    log = tmp_path / "b.log"
    log.write_text("Overfull \\hbox (9.0pt too wide)", encoding="utf-8")
    problems = PdfVerifier(PypdfPdfInspector(), FilesystemManuscriptSource()).verify(
        tmp_path / "b.pdf", tmp_path / "b.toml", log
    )
    assert problems == ["no Contents page found"]


def dashed_book(path: Path) -> None:
    make_pdf(
        path,
        [
            [(100, 560, "Contents"), (100, 540, "Chapter One 1"), (100, 520, "Chapter Two 2")],
            [(200, 612, "1"), (100, 500, "Chapter One"), (100, 480, "Wait \u2014 what is that")],
            [(200, 612, "2"), (100, 500, "Chapter Two"), (100, 480, "Lorem ipsum dolor")],
            [(100, 500, "Copyright First Edition")],
        ],
    )


def verify(tmp_path: Path, config: str) -> list[str]:
    (tmp_path / "b.toml").write_text(config, encoding="utf-8")
    dashed_book(tmp_path / "b.pdf")
    return PdfVerifier(PypdfPdfInspector(), FilesystemManuscriptSource()).verify(
        tmp_path / "b.pdf", tmp_path / "b.toml"
    )


def test_a_novel_interior_may_use_em_dashes(tmp_path: Path) -> None:
    assert verify(tmp_path, CONFIG + 'kind = "novel"\n') == []


def test_a_nonfiction_interior_with_the_same_em_dash_is_refused(tmp_path: Path) -> None:
    assert verify(tmp_path, CONFIG) == ["page 2: contains an em dash"]
    assert verify(tmp_path, CONFIG + 'kind = "nonfiction"\n') == ["page 2: contains an em dash"]


def test_an_unknown_kind_stops_verification_with_a_clear_message(tmp_path: Path) -> None:
    with pytest.raises(ManuscriptError, match="'nonfiction', 'novel' or 'screenplay'"):
        verify(tmp_path, CONFIG + 'kind = "novell"\n')


def sized_book(path: Path, size: tuple[float, float]) -> None:
    make_pdf(
        path,
        [
            [(100, 520, "Contents"), (100, 500, "Chapter One 1"), (100, 480, "Chapter Two 2")],
            [(190, 570, "1"), (100, 460, "Chapter One"), (100, 440, "Lorem ipsum dolor")],
            [(190, 570, "2"), (100, 460, "Chapter Two"), (100, 440, "Lorem ipsum dolor")],
            [(100, 460, "Copyright First Edition")],
        ],
        size,
    )


def verify_sized(tmp_path: Path, config: str, size: tuple[float, float]) -> list[str]:
    (tmp_path / "b.toml").write_text(config, encoding="utf-8")
    sized_book(tmp_path / "b.pdf", size)
    return PdfVerifier(PypdfPdfInspector(), FilesystemManuscriptSource()).verify(
        tmp_path / "b.pdf", tmp_path / "b.toml"
    )


def test_an_interior_at_the_books_own_trim_size_passes(tmp_path: Path) -> None:
    assert verify_sized(tmp_path, CONFIG + 'trim_size = "5.5x8.5"\n', (396, 612)) == []


def test_an_interior_at_another_size_is_refused_with_the_expected_one_named(
    tmp_path: Path,
) -> None:
    problems = verify_sized(tmp_path, CONFIG + 'trim_size = "5.5x8.5"\n', (432, 648))
    assert "page 1 is 432.0 x 648.0 pt, expected 396 x 612" in problems


def test_a_book_that_says_nothing_about_trim_is_still_checked_at_six_by_nine(
    tmp_path: Path,
) -> None:
    assert "expected 432 x 648" in " ".join(verify_sized(tmp_path, CONFIG, (396, 612)))
