"""Cover file writers, the ebook border, and the three KDP verifiers."""

import io
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, NumberObject

from engineering_influence.publishing.covers.cover_files import CoverFiles
from engineering_influence.publishing.covers.ebook_border import EbookBorder
from engineering_influence.publishing.covers.ebook_cover_verifier import EbookCoverVerifier
from engineering_influence.publishing.covers.image_verifier import ImageVerifier
from engineering_influence.publishing.covers.interior_page_count import InteriorPageCount
from engineering_influence.publishing.covers.kdp_cover_spec import KdpCoverSpec
from engineering_influence.publishing.covers.print_pdf_verifier import PrintPdfVerifier
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError

DARK = (20, 20, 40)


def save(
    tmp_path: Path,
    name: str,
    size: tuple[int, int] = (1600, 2560),
    color: Any = DARK,
    mode: str = "RGB",
    **kw: Any,
) -> Path:
    path = tmp_path / name
    Image.new(mode, size, color).save(path, **kw)
    return path


def test_border_detects_light_edges_and_frames_them() -> None:
    border = EbookBorder()
    assert not border.is_light_edge(Image.new("RGB", (200, 300), DARK))
    white = Image.new("RGB", (200, 300), "white")
    assert border.is_light_edge(white)
    framed = border.add(white)
    assert framed.getpixel((0, 0)) == KdpCoverSpec.EBOOK_BORDER_RGB and white.getpixel((0, 0)) == (
        255,
        255,
        255,
    )
    assert framed.getpixel((100, 150)) == (255, 255, 255)


def test_tiff_compression_and_jpeg_dpi(tmp_path: Path) -> None:
    img = Image.new("RGB", (64, 64), DARK)
    files = CoverFiles()
    files.save_tiff(img, tmp_path / "c.tif")
    files.save_tiff(img, tmp_path / "r.tif", compress=False)
    assert Image.open(tmp_path / "c.tif").info["compression"] == "tiff_adobe_deflate"
    assert Image.open(tmp_path / "r.tif").info["compression"] == "raw"
    jpeg = Image.open(io.BytesIO(files.jpeg_bytes(img)))
    assert (
        jpeg.format == "JPEG"
        and round(jpeg.info["dpi"][0]) == 300
        and not jpeg.info.get("progressive")
    )


def test_written_pdf_is_a_single_flat_image_page(tmp_path: Path) -> None:
    pdf = tmp_path / "wrap.pdf"
    CoverFiles().write_pdf(Image.new("RGB", (900, 600), DARK), pdf, 3.0, 2.0, "Title é", "Au Thor")
    assert pdf.read_bytes().startswith(b"%PDF-1.4")
    assert PrintPdfVerifier().run(pdf, 3.0, 2.0) == []
    from pypdf import PdfReader

    info = PdfReader(str(pdf)).metadata
    assert info is not None and info.title == "Title é" and info.author == "Au Thor"


def test_image_verifier(tmp_path: Path) -> None:
    good = save(tmp_path, "good.tif", (300, 300), dpi=(300, 300))
    assert ImageVerifier().run(good, 1.0, 1.0, 300) == []
    wrong_size = save(tmp_path, "size.tif", (310, 300), dpi=(300, 300))
    assert "px, expected (300, 300)" in ImageVerifier().run(wrong_size, 1.0, 1.0, 300)[0]
    bad_dpi = save(tmp_path, "dpi.tif", (300, 300), dpi=(72, 72))
    assert "DPI, expected 300" in ImageVerifier().run(bad_dpi, 1.0, 1.0, 300)[0]
    rgba = save(tmp_path, "rgba.tif", (300, 300), (1, 2, 3, 4), "RGBA", dpi=(300, 300))
    assert "mode RGBA" in ImageVerifier().run(rgba, 1.0, 1.0, 300)[0]
    icc = save(tmp_path, "icc.jpg", (300, 300), dpi=(300, 300), icc_profile=b"profile")
    assert "carries a colour profile" in ImageVerifier().run(icc, 1.0, 1.0, 300)[0]


def test_ebook_verifier_accepts_a_good_cover(tmp_path: Path) -> None:
    assert EbookCoverVerifier().run(save(tmp_path, "ok.jpg")) == []
    assert EbookCoverVerifier().run(save(tmp_path, "ok.tif")) == []


def test_ebook_verifier_rejects_unreadable_files(tmp_path: Path) -> None:
    junk = tmp_path / "junk.jpg"
    junk.write_bytes(b"not an image")
    assert "not a valid image" in EbookCoverVerifier().run(junk)[0]


@pytest.mark.parametrize(
    ("name", "kwargs", "expected"),
    [
        ("p.png", {}, "PNG; KDP takes JPEG or TIFF"),
        ("s.jpg", {"size": (1000, 1700)}, "KDP's ideal is 1600 x 2560"),
        ("t.jpg", {"size": (500, 900)}, "outside KDP's 625 x 1000 to 10,000 px limits"),
        ("r.jpg", {"size": (1600, 2000)}, "height to width is 1.250"),
        ("g.jpg", {"color": 20, "mode": "L"}, "mode L; KDP wants RGB"),
        ("i.jpg", {"icc_profile": b"profile"}, "carries a colour profile"),
        ("c.tif", {"compression": "tiff_adobe_deflate"}, "TIFF compressed with tiff_adobe_deflate"),
        ("pr.jpg", {"progressive": True}, "progressive JPEG"),
        ("w.jpg", {"color": "white"}, "light background with no gray border"),
    ],
)
def test_ebook_verifier_reports_each_defect(
    tmp_path: Path, name: str, kwargs: dict[str, Any], expected: str
) -> None:
    problems = EbookCoverVerifier().run(save(tmp_path, name, **kwargs))
    assert any(expected in p for p in problems), problems


def test_ebook_verifier_accepts_a_light_cover_with_the_border(tmp_path: Path) -> None:
    framed = EbookBorder().add(Image.new("RGB", (1600, 2560), "white"))
    path = tmp_path / "framed.jpg"
    path.write_bytes(CoverFiles().jpeg_bytes(framed))
    assert EbookCoverVerifier().run(path) == []


def test_ebook_verifier_enforces_the_size_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(KdpCoverSpec, "EBOOK_MAX_MB", 0.0001)
    assert "KDP's limit is 0.0001 MB" in EbookCoverVerifier().run(save(tmp_path, "big.jpg"))[0]


def make_pdf(
    tmp_path: Path,
    name: str = "p.pdf",
    size: tuple[float, float] = (216, 144),
    pages: int = 1,
    xobjects: dict[str, Any] | None = None,
    page_extra: dict[str, Any] | None = None,
    encrypt: bool = False,
) -> Path:
    writer = PdfWriter()
    for _ in range(pages):
        page = writer.add_blank_page(*size)
        if xobjects is not None:
            page[NameObject("/Resources")] = DictionaryObject(
                {
                    NameObject("/XObject"): DictionaryObject(
                        {NameObject(f"/I{i}"): v for i, v in enumerate(xobjects.values())}
                    )
                }
            )
        for key, value in (page_extra or {}).items():
            page[NameObject(key)] = value
    if encrypt:
        writer.encrypt("secret")
    path = tmp_path / name
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def image_object(**overrides: Any) -> DictionaryObject:
    base = {
        "/Type": NameObject("/XObject"),
        "/Subtype": NameObject("/Image"),
        "/Width": NumberObject(900),
        "/Height": NumberObject(600),
        "/ColorSpace": NameObject("/DeviceRGB"),
    }
    base.update(overrides)
    return DictionaryObject({NameObject(k): v for k, v in base.items()})


PDF_IN = (3.0, 2.0)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"encrypt": True, "xobjects": {"a": image_object()}}, "encrypted; KDP rejects"),
        ({"pages": 2, "xobjects": {"a": image_object()}}, "2 pages; KDP wants a single page"),
        ({"size": (300, 144), "xobjects": {"a": image_object()}}, "expected 3.0000 x 2.0000 in"),
        (
            {"page_extra": {"/Group": DictionaryObject()}, "xobjects": {"a": image_object()}},
            "transparency group",
        ),
        ({}, "holds no image"),
        (
            {"xobjects": {"a": DictionaryObject({NameObject("/Subtype"): NameObject("/Form")})}},
            "non-image object",
        ),
        (
            {"xobjects": {"a": image_object(**{"/ColorSpace": NameObject("/DeviceGray")})}},
            "colour space /DeviceGray",
        ),
        (
            {"xobjects": {"a": image_object(**{"/SMask": DictionaryObject()})}},
            "image has transparency",
        ),
        (
            {"xobjects": {"a": image_object(**{"/Width": NumberObject(300)})}},
            "100.00 DPI; KDP's minimum is 300",
        ),
    ],
)
def test_print_pdf_verifier_reports_each_defect(
    tmp_path: Path, kwargs: dict[str, Any], expected: str
) -> None:
    problems = PrintPdfVerifier().run(make_pdf(tmp_path, **kwargs), *PDF_IN)
    assert any(expected in p for p in problems), problems


def test_print_pdf_verifier_flags_fonts_and_oversized_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(216, 144)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(),
            NameObject("/XObject"): DictionaryObject({NameObject("/I"): image_object()}),
        }
    )
    path = tmp_path / "fonts.pdf"
    with path.open("wb") as handle:
        writer.write(handle)
    assert any("uses fonts" in p for p in PrintPdfVerifier().run(path, *PDF_IN))
    monkeypatch.setattr(KdpCoverSpec, "PDF_MAX_MB", 0.00001)
    assert any(
        "KDP recommends 1e-05 MB or less" in p for p in PrintPdfVerifier().run(path, *PDF_IN)
    )


def test_print_pdf_verifier_rejects_unreadable_files(tmp_path: Path) -> None:
    path = tmp_path / "bad.pdf"
    path.write_bytes(b"definitely not a pdf")
    assert "not a readable PDF" in PrintPdfVerifier().run(path, *PDF_IN)[0]


def test_interior_page_count(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path, pages=7)
    assert InteriorPageCount().of(pdf) == 7
    with pytest.raises(BookBuildError, match="build the interior first"):
        InteriorPageCount().of(tmp_path / "absent.pdf")


def test_an_encrypted_pdf_is_reported_without_being_read(tmp_path: Path) -> None:
    problems = PrintPdfVerifier().run(make_pdf(tmp_path, encrypt=True), *PDF_IN)
    assert problems == ["p.pdf: encrypted; KDP rejects secured files"]
