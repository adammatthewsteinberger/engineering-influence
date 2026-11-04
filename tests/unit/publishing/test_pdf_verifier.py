"""End-to-end verification of a small generated interior."""

from pathlib import Path

from reportlab.pdfgen import canvas

from engineering_influence.publishing.pdf_verifier import PdfVerifier

CONFIG = 'title = "Test Book"\nedition = "First Edition"\n'


def make_pdf(path: Path, pages: list[list[tuple[float, float, str]]]) -> None:
    pdf = canvas.Canvas(str(path), pagesize=(432, 648))
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
    assert PdfVerifier().verify(tmp_path / "b.pdf", tmp_path / "b.toml") == []


def test_log_problems_are_included_when_log_exists(tmp_path: Path) -> None:
    (tmp_path / "b.toml").write_text(CONFIG, encoding="utf-8")
    book(tmp_path / "b.pdf")
    log = tmp_path / "b.log"
    log.write_text("Overfull \\hbox (9.0pt too wide)", encoding="utf-8")
    problems = PdfVerifier().verify(tmp_path / "b.pdf", tmp_path / "b.toml", log)
    assert problems == ["1 overfull lines (worst 9.0pt)"]
    missing = tmp_path / "absent.log"
    assert PdfVerifier().verify(tmp_path / "b.pdf", tmp_path / "b.toml", missing) == []


def test_book_without_contents_stops_before_the_log(tmp_path: Path) -> None:
    (tmp_path / "b.toml").write_text(CONFIG, encoding="utf-8")
    make_pdf(tmp_path / "b.pdf", [[(100, 500, "First Edition")]])
    log = tmp_path / "b.log"
    log.write_text("Overfull \\hbox (9.0pt too wide)", encoding="utf-8")
    problems = PdfVerifier().verify(tmp_path / "b.pdf", tmp_path / "b.toml", log)
    assert problems == ["no Contents page found"]
