"""PDF-facing checks, driven by fake pages and small generated PDFs."""

import io
from typing import Any

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject

from engineering_influence.publishing.folio_reader import FolioReader
from engineering_influence.publishing.pdf_layout_check import PdfLayoutCheck
from engineering_influence.publishing.pdf_structure_check import PdfStructureCheck


class FakePage:
    def __init__(
        self,
        chars: list[dict[str, float]] | None = None,
        words: list[dict[str, Any]] | None = None,
        text: str = "",
    ) -> None:
        self.chars = chars or []
        self._words = words or []
        self._text = text
        self.width = 432.0
        self.height = 648.0

    def extract_words(self, **_: Any) -> list[dict[str, Any]]:
        return self._words

    def extract_text(self, **_: Any) -> str:
        return self._text


def box(x0: float, x1: float, top: float = 100, bottom: float = 500) -> FakePage:
    return FakePage(chars=[{"x0": x0, "x1": x1, "top": top, "bottom": bottom}], text="t")


def word(text: str, top: float) -> dict[str, Any]:
    return {"text": text, "top": top, "bottom": top + 8}


def test_folio_prefers_running_head_and_ignores_body_numbers() -> None:
    words = [word("12", 600), word("iv", 20), word("Hello", 25), word("7", 300)]
    assert FolioReader().read(FakePage(words=words)) == "iv"


def test_folio_is_none_without_candidates() -> None:
    assert FolioReader().read(FakePage(words=[word("Hello", 20)])) is None


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
    blank = FakePage()
    problems, _, _ = PdfLayoutCheck().run([blank, blank, blank, box(100, 330), blank, blank])
    assert problems == ["more than two consecutive blank pages ending at page 3"]


def read_back(writer: PdfWriter) -> PdfReader:
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return PdfReader(buffer)


def font(base: str, embedded: bool) -> DictionaryObject:
    descriptor = DictionaryObject({NameObject("/FontName"): NameObject(base)})
    if embedded:
        descriptor[NameObject("/FontFile2")] = DictionaryObject()
    return DictionaryObject(
        {NameObject("/BaseFont"): NameObject(base), NameObject("/FontDescriptor"): descriptor}
    )


def test_structure_accepts_clean_trim_page() -> None:
    writer = PdfWriter()
    writer.add_blank_page(432, 648)
    assert PdfStructureCheck().run(read_back(writer)) == []


def test_structure_reports_size_bookmarks_annotations_and_groups() -> None:
    writer = PdfWriter()
    writer.add_blank_page(400, 600)
    page = writer.add_blank_page(432, 648)
    page[NameObject("/Annots")] = ArrayObject()
    page[NameObject("/Group")] = DictionaryObject()
    writer.add_outline_item("Chapter", 0)
    problems = PdfStructureCheck().run(read_back(writer))
    assert "PDF has bookmarks; KDP print interiors should not" in problems
    assert "page 1 is 400.0 x 600.0 pt, expected 432 x 648" in problems
    assert "page 2 has annotations or links" in problems
    assert "page 2 has a transparency group" in problems


def test_structure_reports_only_unembedded_fonts() -> None:
    writer = PdfWriter()
    writer.add_blank_page(432, 648)  # no resources at all
    page = writer.add_blank_page(432, 648)
    type0 = DictionaryObject({NameObject("/DescendantFonts"): ArrayObject([font("/Wide", False)])})
    fonts = DictionaryObject(
        {
            NameObject("/F1"): font("/Bare", False),
            NameObject("/F2"): font("/Good", True),
            NameObject("/F3"): DictionaryObject({NameObject("/BaseFont"): NameObject("/Std")}),
            NameObject("/F4"): type0,
        }
    )
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): fonts})
    third = writer.add_blank_page(432, 648)
    third[NameObject("/Resources")] = DictionaryObject()  # resources without fonts
    assert PdfStructureCheck().run(read_back(writer)) == [
        "font not embedded: /Bare",
        "font not embedded: /Wide",
    ]
