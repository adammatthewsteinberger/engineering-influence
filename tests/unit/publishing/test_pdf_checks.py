"""PDF-facing checks: rules over plain facts, and the inspector that reads real PDFs."""

from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject
from reportlab.pdfgen import canvas

from engineering_influence.infrastructure.publishing.pypdf_pdf_inspector import PypdfPdfInspector
from engineering_influence.models.publishing.pdf_document import PdfDocument
from engineering_influence.models.publishing.pdf_page import PdfPage
from engineering_influence.models.publishing.pdf_word import PdfWord
from engineering_influence.services.publishing.folio_reader import FolioReader
from engineering_influence.services.publishing.pdf_layout_check import PdfLayoutCheck
from engineering_influence.services.publishing.pdf_structure_check import PdfStructureCheck


def page(
    text_box: tuple[float, float, float, float] | None = None,
    words: tuple[PdfWord, ...] = (),
    text: str = "",
) -> PdfPage:
    return PdfPage(432.0, 648.0, 432.0, 648.0, text, words, text_box, False, False, frozenset())


def box(x0: float, x1: float, top: float = 100, bottom: float = 500) -> PdfPage:
    return page((x0, x1, top, bottom), text="t")


def word(text: str, top: float) -> PdfWord:
    return PdfWord(text, top, top + 8)


def test_folio_prefers_running_head_and_ignores_body_numbers() -> None:
    words = [word("12", 600), word("iv", 20), word("Hello", 25), word("7", 300)]
    assert FolioReader().read(page(words=tuple(words))) == "iv"


def test_folio_is_none_without_candidates() -> None:
    assert FolioReader().read(page(words=(word("Hello", 20),))) is None


def test_layout_accepts_page_inside_margins() -> None:
    problems, texts, folios = PdfLayoutCheck().run([box(100, 330), box(100, 330)])
    assert (problems, texts, folios) == ([], ["t", "t"], [None, None])


def test_layout_reports_recto_gutter_and_outside_violations() -> None:
    problems, _, _ = PdfLayoutCheck().run([box(10, 430)])
    assert any("from the gutter (KDP minimum 0.375 in for 1 pages)" in p for p in problems)
    assert any("from the outside edge" in p for p in problems)


def test_layout_treats_verso_pages_mirrored() -> None:
    problems, _, _ = PdfLayoutCheck().run([box(100, 330), box(100, 425)])
    assert any(p.startswith("page 2") and "gutter" in p for p in problems)


def test_layout_reports_top_and_bottom_edges() -> None:
    problems, _, _ = PdfLayoutCheck().run([box(100, 330, top=5), box(100, 330, bottom=640)])
    assert sum("top or bottom edge" in p for p in problems) == 2


def test_layout_reports_third_consecutive_blank_page_only() -> None:
    blank = page()
    problems, _, _ = PdfLayoutCheck().run([blank, blank, blank, box(100, 330), blank, blank])
    assert problems == ["more than two consecutive blank pages ending at page 3"]


def inspected(writer: PdfWriter, tmp_path: Path) -> PdfDocument:
    path = tmp_path / "x.pdf"
    writer.write(str(path))
    return PypdfPdfInspector().inspect(path)


def font(base: str, embedded: bool) -> DictionaryObject:
    descriptor = DictionaryObject({NameObject("/FontName"): NameObject(base)})
    if embedded:
        descriptor[NameObject("/FontFile2")] = DictionaryObject()
    return DictionaryObject(
        {NameObject("/BaseFont"): NameObject(base), NameObject("/FontDescriptor"): descriptor}
    )


def test_structure_accepts_clean_trim_page(tmp_path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(432, 648)
    assert PdfStructureCheck().run(inspected(writer, tmp_path)) == []


def test_structure_reports_size_bookmarks_annotations_and_groups(tmp_path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(400, 600)
    second = writer.add_blank_page(432, 648)
    second[NameObject("/Annots")] = ArrayObject()
    second[NameObject("/Group")] = DictionaryObject()
    writer.add_outline_item("Chapter", 0)
    problems = PdfStructureCheck().run(inspected(writer, tmp_path))
    assert "PDF has bookmarks; KDP print interiors should not" in problems
    assert "page 1 is 400.0 x 600.0 pt, expected 432 x 648" in problems
    assert "page 2 has annotations or links" in problems
    assert "page 2 has a transparency group" in problems


def test_structure_reports_only_unembedded_fonts(tmp_path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(432, 648)  # no resources at all
    second = writer.add_blank_page(432, 648)
    type0 = DictionaryObject({NameObject("/DescendantFonts"): ArrayObject([font("/Wide", False)])})
    fonts = DictionaryObject(
        {
            NameObject("/F1"): font("/Bare", False),
            NameObject("/F2"): font("/Good", True),
            NameObject("/F3"): DictionaryObject({NameObject("/BaseFont"): NameObject("/Std")}),
            NameObject("/F4"): type0,
        }
    )
    second[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): fonts})
    third = writer.add_blank_page(432, 648)
    third[NameObject("/Resources")] = DictionaryObject()  # resources without fonts
    assert PdfStructureCheck().run(inspected(writer, tmp_path)) == [
        "font not embedded: /Bare",
        "font not embedded: /Wide",
    ]


def test_the_inspector_reads_text_words_and_the_box_of_a_page(tmp_path: Path) -> None:
    path = tmp_path / "b.pdf"
    pdf = canvas.Canvas(str(path), pagesize=(432, 648))
    pdf.drawString(100, 500, "Hello world")
    pdf.showPage()
    pdf.showPage()  # a blank page
    pdf.save()

    document = PypdfPdfInspector().inspect(path)

    written, blank = document.pages
    assert written.text == "Hello world"
    assert [w.text for w in written.words] == ["Hello", "world"]
    assert written.text_box is not None and written.text_box[0] == 100
    assert (written.width, written.height) == (432, 648)
    assert blank.text == "" and blank.words == () and blank.text_box is None
    assert not document.has_outline


def test_page_count_is_none_for_a_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "b.pdf"
    assert PypdfPdfInspector().page_count(path) is None
    writer = PdfWriter()
    writer.add_blank_page(432, 648)
    writer.add_blank_page(432, 648)
    writer.write(str(path))
    assert PypdfPdfInspector().page_count(path) == 2
