"""Each verifier branch, driven by corrupting a known-good finished EPUB one way at a time."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import jpeg_bytes, regex_sub

from engineering_influence.publishing.epub.epub_verifier import EpubVerifier
from engineering_influence.publishing.epub.epubcheck_runner import EpubcheckRunner
from engineering_influence.publishing.typesetting.book import Book

Rewrite = Callable[..., Path]
NO_GUIDE = regex_sub(r"<guide>.*?</guide>", "")
TWO_SPINE = (
    '<itemref idref="toc"/><itemref idref="p0"/>',
    '<itemref idref="p0"/><itemref idref="toc"/>',
)

CASES: dict[str, tuple[dict[str, Any], str]] = {
    "mimetype": ({"first": "a.txt"}, "mimetype is not the first, uncompressed entry"),
    "css": ({"edits": {"demo.css": lambda s: s + "\n.x { display: none }\n"}}, "hides an element"),
    "entity": (
        {
            "edits": {
                "c1.xhtml": lambda s: s.replace(
                    "<!DOCTYPE html>", '<!DOCTYPE html [<!ENTITY a "b">]>'
                )
            }
        },
        "c1.xhtml declares XML entities",
    ),
    "malformed": (
        {"edits": {"c1.xhtml": lambda s: s.replace("</body>", "")}},
        "c1.xhtml is not well-formed XML",
    ),
    "em dash": (
        {"edits": {"c1.xhtml": lambda s: s.replace("one text", "one — text")}},
        "contains an em dash",
    ),
    "en dash": (
        {"edits": {"c1.xhtml": lambda s: s.replace("one text", "one – text")}},
        "contains an en dash",
    ),
    "marker": (
        {"edits": {"c1.xhtml": lambda s: s.replace("one text", "[CALLOUT x")}},
        "marker '[CALLOUT' appears",
    ),
    "draft": (
        {"edits": {"c1.xhtml": lambda s: s.replace("one text", "Draft text")}},
        "word 'Draft' appears",
    ),
    "straight quote": (
        {"edits": {"c1.xhtml": lambda s: s.replace("one text", 'say "hi"')}},
        "straight double quote",
    ),
    "edition": (
        {"edits": {"fore.xhtml": lambda s: s.replace("First Edition", "Other")}},
        "edition line 'First Edition' not found",
    ),
    "no nav in opf": (
        {"edits": {"demo.opf": regex_sub(r'<item href="nav.xhtml".*?</item>', "")}},
        "no navigation document found",
    ),
    "entry count": (
        {"edits": {"nav.xhtml": regex_sub(r"<li><a href=\"fore.xhtml[^>]*>[^<]*</a></li>", "", 1)}},
        "contents has 5 entries, expected 6",
    ),
    "missing file": (
        {"edits": {"nav.xhtml": lambda s: s.replace('href="c1.xhtml', 'href="zzz.xhtml')}},
        "contents links to missing file zzz.xhtml",
    ),
    "missing anchor": (
        {"edits": {"nav.xhtml": lambda s: s.replace("#h3", "#nope")}},
        "contents links to missing anchor c1.xhtml#nope",
    ),
    "anchor not on heading": (
        {
            "edits": {
                "nav.xhtml": lambda s: s.replace("#h3", "#para"),
                "c1.xhtml": lambda s: s.replace("<p>Chapter one", "<p id='para'>Chapter one"),
            }
        },
        "c1.xhtml#para does not target a heading element's own id",
    ),
    "ncx differs": (
        {"edits": {"demo.ncx": lambda s: s.replace("<text>1. One", "<text>1. Uno")}},
        "do not list the same entries",
    ),
    "nav broken xml": (
        {"replace": {"nav.xhtml": b"<<not xml"}},
        "nav.xhtml is not well-formed XML",
    ),
    "nav entity": (
        {
            "edits": {
                "nav.xhtml": lambda s: s.replace(
                    "<html", '<!DOCTYPE html [<!ENTITY a "b">]><html', 1
                )
            }
        },
        "nav.xhtml declares XML entities",
    ),
    "ncx broken xml": ({"replace": {"demo.ncx": b"<<not xml"}}, "demo.ncx is not well-formed XML"),
    "landmark anchor": (
        {
            "edits": {
                "nav.xhtml": lambda s: s.replace(
                    'epub:type="toc" href="toc.xhtml"', 'epub:type="toc" href="toc.xhtml#x"'
                )
            }
        },
        "toc landmark points at an anchor",
    ),
    "nav in spine": (
        {"edits": {"demo.opf": lambda s: s.replace("</spine>", '<itemref idref="nav"/></spine>')}},
        "is in the spine",
    ),
    "no guide": ({"edits": {"demo.opf": NO_GUIDE}}, "OPF guide has no toc reference"),
    "landmark mismatch": (
        {
            "edits": {
                "nav.xhtml": lambda s: s.replace(
                    'epub:type="toc" href="toc.xhtml"', 'epub:type="toc" href="c1.xhtml"'
                )
            }
        },
        "landmark and the OPF guide do not name the same contents page",
    ),
    "page is nav": (
        {
            "edits": {
                "demo.opf": lambda s: s.replace(
                    'type="toc" title="Contents" href="toc.xhtml"',
                    'type="toc" title="Contents" href="nav.xhtml"',
                ),
                "nav.xhtml": lambda s: s.replace(
                    'epub:type="toc" href="toc.xhtml"', 'epub:type="toc" href="nav.xhtml"'
                ),
            }
        },
        "contents page is the navigation document",
    ),
    "page not in spine": (
        {
            "edits": {
                "demo.opf": lambda s: s.replace(
                    'type="toc" title="Contents" href="toc.xhtml"',
                    'type="toc" title="Contents" href="ghost.xhtml"',
                ),
                "nav.xhtml": lambda s: s.replace(
                    'epub:type="toc" href="toc.xhtml"', 'epub:type="toc" href="ghost.xhtml"'
                ),
            }
        },
        "contents page ghost.xhtml is not in the spine",
    ),
    "page has nav": (
        {"edits": {"toc.xhtml": lambda s: s.replace("<body>", "<body><nav>x</nav>")}},
        "contents page contains a <nav> element",
    ),
    "page after chapter": (
        {"edits": {"demo.opf": lambda s: s.replace(*TWO_SPINE)}},
        "contents page comes after the first chapter",
    ),
    "page links differ": (
        {"edits": {"toc.xhtml": lambda s: s.replace(">Foreword<", ">Forward<")}},
        "does not list the NCX's entries",
    ),
    "internal missing file": (
        {
            "edits": {
                "c1.xhtml": lambda s: s.replace(
                    "<p>Chapter one", '<p><a href="ghost.xhtml">g</a></p><p>Chapter one'
                )
            }
        },
        "c1.xhtml links to missing file ghost.xhtml",
    ),
    "internal missing anchor": (
        {
            "edits": {
                "c1.xhtml": lambda s: s.replace(
                    "<p>Chapter one", '<p><a href="c2.xhtml#nope">g</a></p><p>Chapter one'
                )
            }
        },
        "c1.xhtml links to missing anchor c2.xhtml#nope",
    ),
    "empty title": (
        {"edits": {"c1.xhtml": lambda s: s.replace("<title>T</title>", "<title> </title>")}},
        "c1.xhtml has an empty <title>",
    ),
    "empty paragraph": (
        {"edits": {"c1.xhtml": lambda s: s.replace("<p>Chapter one", "<p> </p><p>Chapter one")}},
        "c1.xhtml has empty paragraphs",
    ),
    "no bodymatter": (
        {"edits": {"nav.xhtml": lambda s: s.replace('epub:type="bodymatter"', 'epub:type="x"')}},
        "no bodymatter landmark",
    ),
    "no guide text": (
        {
            "edits": {
                "demo.opf": lambda s: s.replace('<reference type="text"', '<reference type="x"')
            }
        },
        "no guide reference for the start of the text",
    ),
    "no cover item": (
        {"edits": {"demo.opf": regex_sub(r'<item href="cover.jpg".*?</item>', "")}},
        "declares no cover image",
    ),
    "cover not jpeg": (
        {
            "edits": {
                "demo.opf": lambda s: s.replace('media-type="image/jpeg"', 'media-type="image/png"')
            }
        },
        "not declared as image/jpeg",
    ),
    "no cover meta": (
        {"edits": {"demo.opf": lambda s: s.replace('<meta name="cover"', '<meta name="x"')}},
        'no <meta name="cover">',
    ),
    "cover missing": ({"drop": ("cover.jpg",)}, "cover image cover.jpg is missing from the EPUB"),
    "cover garbage": ({"replace": {"cover.jpg": b"not an image"}}, "cover image does not decode"),
    "cover png": (
        {"replace": {"cover.jpg": jpeg_bytes((1600, 2500), "RGBA", "PNG")}},
        "expected an RGB JPEG",
    ),
    "cover small": (
        {"replace": {"cover.jpg": jpeg_bytes((100, 100))}},
        "KDP wants at least 1600 x 2500",
    ),
    "image on page": (
        {
            "edits": {
                "c1.xhtml": lambda s: s.replace(
                    "<p>Chapter one", '<p><img src="cover.jpg"/></p><p>Chapter one'
                )
            }
        },
        "shows an image",
    ),
}


def test_the_known_good_fixture_has_no_problems(finished: Path, book: Book) -> None:
    assert EpubVerifier().verify(finished, book) == []


@pytest.mark.parametrize("label", sorted(CASES))
def test_each_defect_is_reported(label: str, finished: Path, book: Book, rewrite: Rewrite) -> None:
    kwargs, expected = CASES[label]
    problems = EpubVerifier().verify(rewrite(finished, **kwargs), book)
    assert any(expected in problem for problem in problems), problems


def test_a_same_file_anchor_link_resolves(finished: Path, book: Book, rewrite: Rewrite) -> None:
    mutant = rewrite(
        finished,
        edits={
            "c1.xhtml": lambda s: s.replace(
                "<p>Chapter one", '<p><a href="#h3">up</a></p><p>Chapter one'
            )
        },
    )
    assert EpubVerifier().verify(mutant, book) == []


def test_external_and_stylesheet_links_are_not_resolved(
    finished: Path, book: Book, rewrite: Rewrite
) -> None:
    links = (
        '<p><a href="https://e.example">e</a><a href="mailto:a@b.c">m</a><a href="x.css">c</a></p>'
    )
    mutant = rewrite(
        finished,
        edits={"c1.xhtml": lambda s: s.replace("<p>Chapter one", links + "<p>Chapter one")},
    )
    assert EpubVerifier().verify(mutant, book) == []


def test_epubcheck_findings_are_appended(finished: Path, book: Book) -> None:
    class Fake(EpubcheckRunner):
        def run(self, path: Path) -> list[str]:
            return ["epubcheck: ERROR something"]

    assert EpubVerifier(Fake()).verify(finished, book) == ["epubcheck: ERROR something"]
