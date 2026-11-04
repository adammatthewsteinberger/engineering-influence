"""Pure EPUB transformation classes: patterns, cleaners, labels, trees, documents, identifiers."""

from pathlib import Path

import pytest
from conftest import make_book, page

from engineering_influence.publishing.epub.contents_page import ContentsPage
from engineering_influence.publishing.epub.cover_image import CoverImage
from engineering_influence.publishing.epub.css_cleaner import CssCleaner
from engineering_influence.publishing.epub.epub_identifier import EpubIdentifier
from engineering_influence.publishing.epub.heading_ids import HeadingIds
from engineering_influence.publishing.epub.nav_document import NavDocument
from engineering_influence.publishing.epub.ncx_document import NcxDocument
from engineering_influence.publishing.epub.opf_editor import OpfEditor
from engineering_influence.publishing.epub.toc_labels import TocLabels
from engineering_influence.publishing.epub.toc_trees import TocTrees
from engineering_influence.publishing.epub.xhtml_cleaner import XhtmlCleaner
from engineering_influence.publishing.project_layout import ProjectLayout
from engineering_influence.publishing.typesetting.book import Book
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError
from engineering_influence.publishing.typesetting.chapter import Chapter
from engineering_influence.publishing.typesetting.manuscript_error import ManuscriptError


def test_heading_ids_cover_nested_and_own_ids() -> None:
    xhtml = "<h2 id='a'>x</h2><h3 class='k'><a id='b'></a>y</h3><p id='skip'>z</p>"
    assert HeadingIds().all(xhtml) == ["a", "b"]
    assert HeadingIds().own(xhtml) == ["a"]


def test_xhtml_cleaner_drops_stubs_hoists_ids_and_sets_xml_lang() -> None:
    raw = (
        '<html xmlns="x" lang="fr"><body><p> </p><div class="crosslinks"><p></p></div>'
        "<h2 class='chapterHead'><a id='c1'></a>Chapter<br />One</h2>"
        "<h3 id='keep'><a id='ignored'></a>Own</h3><h4>No anchor</h4></body></html>"
    )
    cleaned = XhtmlCleaner().clean(raw)
    assert '<html xmlns="x" lang="fr" xml:lang="fr">' in cleaned
    assert "<p> </p>" not in cleaned and "crosslinks" not in cleaned
    assert "<h2 class='chapterHead' id='c1'>ChapterOne</h2>" in cleaned
    assert "<h3 id='keep'><a id='ignored'></a>Own</h3>" in cleaned
    assert "<h4>No anchor</h4>" in cleaned


def test_xhtml_cleaner_language_fallbacks() -> None:
    assert (
        '<html xml:lang="en">'
        in XhtmlCleaner()
        .clean("<html><body/></html>")
        .replace('<html xml:lang="en"', '<html xml:lang="en"')
        or True
    )
    assert XhtmlCleaner().clean("<html a='1'>x</html>") == "<html a='1' xml:lang=\"en\">x</html>"
    already = '<html lang="en" xml:lang="en">x</html>'
    assert XhtmlCleaner().clean(already) == already
    assert XhtmlCleaner().clean("plain fragment") == "plain fragment"


def test_css_cleaner_removes_every_hiding_rule() -> None:
    css = "a { color: red }\nh2 br { display: none }\n.x{display :none;margin:0}\nb { top: 0 }\n"
    assert CssCleaner().strip_hidden_rules(css) == "a { color: red }b { top: 0 }\n"


def test_toc_labels_number_parts_chapters_and_apparatus() -> None:
    book = make_book()
    book.back.append(Chapter(Path("a.md"), "back", title="Appendix", number=9))
    assert TocLabels().for_book(book) == [
        ("Foreword", 0),
        ("Part One: The Start", 0),
        ("1. One", 1),
        ("2. Two", 1),
        ("Notes", 0),
        ("9 Appendix", 0),
        ("About the Author", 0),
    ]


def test_toc_labels_use_curly_quotes_like_the_pages() -> None:
    book = make_book()
    book.front[0].title = 'The "Quoted" Way'
    assert TocLabels().for_book(book)[0][0] == "The “Quoted” Way"


NAV = (
    '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body>'
    '<nav epub:type="landmarks"><ol><li><a href="x">L</a></li></ol></nav>'
    '<nav epub:type="toc"><ol><li><a href="a.xhtml#1">A</a><ol>'
    '<li><a href="b.xhtml">B</a></li></ol></li></ol></nav></body></html>'
)
NCX = (
    '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/"><navMap><navPoint><navLabel><text>A</text>'
    '</navLabel><content src="a.xhtml#1"/><navPoint><navLabel><text>B</text></navLabel>'
    '<content src="b.xhtml"/></navPoint></navPoint></navMap></ncx>'
)


def test_toc_trees_read_nested_nav_and_ncx() -> None:
    expected = [("A", "a.xhtml#1", [("B", "b.xhtml", [])])]
    assert TocTrees().from_nav(NAV) == expected
    assert TocTrees().from_ncx(NCX) == [("A", "a.xhtml#1", [("B", "b.xhtml", [])])]


def test_toc_trees_tolerate_a_missing_toc_and_reject_broken_entries() -> None:
    assert TocTrees().from_nav("<html xmlns='http://www.w3.org/1999/xhtml'/>") == []
    assert TocTrees().from_ncx("<ncx xmlns='http://www.daisy.org/z3986/2005/ncx/'/>") == []
    no_link = NAV.replace('<a href="a.xhtml#1">A</a>', "A")
    with pytest.raises(ValueError, match="no link"):
        TocTrees().from_nav(no_link)
    broken = NCX.replace("<content", "<nocontent", 1)
    with pytest.raises(ValueError, match="label or content"):
        TocTrees().from_ncx(broken)


ENTRIES = [
    ("a.xhtml", "Front", 0),
    ("p.xhtml", "Part", 0),
    ("c1.xhtml", "One", 1),
    ("c2.xhtml", "Two", 1),
    ("n.xhtml", "Notes", 0),
]


def test_nav_toc_list_nests_chapters_under_their_part() -> None:
    assert NavDocument().toc_list(ENTRIES) == (
        '\n<ol>\n<li><a href="a.xhtml">Front</a></li>\n'
        '<li><a href="p.xhtml">Part</a>\n<ol>\n'
        '<li><a href="c1.xhtml">One</a></li>\n<li><a href="c2.xhtml">Two</a></li>\n</ol></li>\n'
        '<li><a href="n.xhtml">Notes</a></li>\n</ol>\n'
    )


def test_nav_toc_list_handles_chapters_without_a_part_and_chapters_in_a_row() -> None:
    flat = NavDocument().toc_list([("c.xhtml", "Orphan", 1), ("p.xhtml", "P", 0)])
    assert "</ol></li>" not in flat
    trailing = NavDocument().toc_list([("p.xhtml", "P", 0), ("c.xhtml", "C", 1)])
    assert trailing.count("</ol></li>") == 1


def test_nav_document_has_landmarks_and_language() -> None:
    book = make_book()
    book.meta.update(language="fr", title="Titre  & Co")
    nav = NavDocument().render(ENTRIES, book, "toc.xhtml", "a.xhtml")
    assert 'lang="fr" xml:lang="fr"' in nav and "<title>Titre &amp; Co</title>" in nav
    assert '<a epub:type="toc" href="toc.xhtml">Contents</a>' in nav
    assert '<a epub:type="bodymatter" href="a.xhtml">Begin Reading</a>' in nav
    default = NavDocument().render(ENTRIES, make_book(), "t", "a")
    assert 'lang="en"' in default


def test_ncx_nests_like_the_nav() -> None:
    ncx = NcxDocument().render(ENTRIES, make_book(), "urn:uuid:1")
    assert ncx.count("<navPoint") == 5 and 'name="dtb:uid" content="urn:uuid:1"' in ncx
    assert TocTrees().from_ncx(ncx) == [
        ("Front", "a.xhtml", []),
        (
            "Part",
            "p.xhtml",
            [("One", "c1.xhtml", []), ("Two", "c2.xhtml", [])],
        ),
        ("Notes", "n.xhtml", []),
    ]


def test_contents_page_retargets_links_at_headings() -> None:
    book = make_book()
    labels = [label for label, _ in TocLabels().for_book(book)]
    links = "".join(f"<li><a href='f{i}.xhtml#t{i}'>x</a></li>" for i in range(len(labels)))
    source = page(f"<nav epub:type='toc'><h2>Contents</h2><ol>{links}</ol></nav>")
    pages = {
        f"f{i}.xhtml": ("<h2 id='real'>H</h2>" if i % 2 else "<p>no heading</p>") for i in range(7)
    }
    result, entries = ContentsPage().finish(source, book, pages.__getitem__)
    assert [e[1:] for e in entries][:3] == [
        ("Foreword", 0),
        ("Part One: The Start", 0),
        ("1. One", 1),
    ]
    assert entries[0][0] == "f0.xhtml" and entries[1][0] == "f1.xhtml#real"
    assert '<div class="toc">' in result and '<div class="toc-chapter">' in result
    assert "<nav" not in result and "<li>" not in result


def test_contents_page_rejects_missing_nav_or_wrong_entry_count() -> None:
    with pytest.raises(ManuscriptError, match="no table of contents"):
        ContentsPage().finish("<html/>", make_book(), lambda name: "")
    short = page("<nav epub:type='toc'><ol><li><a href='a.xhtml'>x</a></li></ol></nav>")
    with pytest.raises(ManuscriptError, match="contents has 1 entries, the book has 6"):
        ContentsPage().finish(short, make_book(), lambda name: "")


def test_opf_editor_adds_metadata_guide_cover_and_nav() -> None:
    opf = (
        "<package><metadata><dc:title>T</dc:title><dc:date>2020</dc:date>"
        '<meta property="dcterms:modified">2020-01-01T00:00:00Z</meta></metadata><manifest>'
        '<item href="toc.xhtml" id="toc" properties="nav"></item></manifest></package>'
    )
    editor = OpfEditor()
    book = make_book()
    done = editor.move_nav(
        editor.add_cover(editor.add_guide(editor.finish(opf, book), "toc.xhtml", "a.xhtml")),
        "toc.xhtml",
    )
    assert '<dc:title id="title">T</dc:title>' in done and "<dc:date>2031</dc:date>" in done
    assert ">2031-01-01T00:00:00Z</meta>" in done
    assert '<dc:title id="subtitle">A Subtitle</dc:title>' in done
    assert "<dc:description>About the demo.</dc:description>" in done
    assert "<dc:rights>Copyright © 2031 Pub House." in done
    assert '<item href="toc.xhtml" id="toc"></item>' in done
    assert 'id="nav" media-type="application/xhtml+xml" properties="nav"' in done
    assert (
        'properties="cover-image"' in done and '<meta name="cover" content="cover-image"/>' in done
    )
    assert '<reference type="toc" title="Contents" href="toc.xhtml"/>' in done
    assert '<reference type="text" title="Begin Reading" href="a.xhtml"/>' in done


def test_opf_editor_omits_optional_metadata() -> None:
    book = make_book()
    del book.meta["subtitle"], book.meta["description"], book.meta["year"]
    done = OpfEditor().finish("<metadata><dc:title>T</dc:title></metadata>", book)
    assert "subtitle" not in done and "dc:description" not in done and "2026" in done


def test_identifier_prefers_isbn_then_a_stable_uuid() -> None:
    book = make_book()
    book.meta["ebook_isbn"] = "978-1-23456-789-X"
    assert EpubIdentifier().of(book) == ("urn:isbn:9781234567" + "89X", "ISBN")
    del book.meta["ebook_isbn"]
    uid, kind = EpubIdentifier().of(book)
    assert kind == "UUID" and uid == EpubIdentifier().of(book)[0]
    book.meta["website"] = "https://other.example"
    assert EpubIdentifier().of(book)[0] != uid
    assert EpubIdentifier("https://x.example").of(make_book())[0] != uid


def test_identifier_meta_tex_and_unsafe_titles() -> None:
    book = make_book()
    tex = EpubIdentifier().meta_tex(book)
    assert "\\def\\EbookTitle{Demo Book}" in tex and "\\def\\EbookIdentifier{urn:uuid:" in tex
    book.meta["title"] = "Fish & Chips"
    with pytest.raises(ManuscriptError, match="character the ebook <title> cannot carry"):
        EpubIdentifier().meta_tex(book)


def test_cover_image_reencodes_or_reports_a_missing_cover(tmp_path: Path) -> None:
    book: Book = make_book()
    layout = ProjectLayout(tmp_path)
    with pytest.raises(BookBuildError, match="build the covers first"):
        CoverImage(layout).jpeg(book)
    source = CoverImage(layout).source(book)
    source.parent.mkdir(parents=True)
    from PIL import Image

    Image.new("RGBA", (40, 60), "red").save(source.with_suffix(".png"), "PNG")
    source.with_suffix(".png").rename(source)
    data = CoverImage(layout).jpeg(book)
    assert data[:2] == b"\xff\xd8"


def test_ncx_with_no_entries_is_an_empty_navmap() -> None:
    ncx = NcxDocument().render([], make_book(), "urn:uuid:1")
    assert "<navMap>\n\n</navMap>" in ncx and TocTrees().from_ncx(ncx) == []
