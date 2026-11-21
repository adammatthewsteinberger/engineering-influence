"""Untrusted text must never become live TeX.

Every place a manuscript, a book config or a model's output reaches the LaTeX generator is
filled with a tripwire, ``}\\EIcanary{``: a brace that would close the surrounding group, then a
macro name. If any path leaves the backslash live, ``\\EIcanary`` appears in the generated TeX
and the test fails. The generator's own commands never contain that name.
"""

import re
from pathlib import Path
from typing import Any

import pytest

from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.models.typesetting.book import Book
from engineering_influence.models.typesetting.chapter import Chapter
from engineering_influence.services.typesetting.chapter_tex import ChapterTex
from engineering_influence.services.typesetting.ebook_document import EbookDocument
from engineering_influence.services.typesetting.markdown_latex_converter import (
    MarkdownLatexConverter,
)
from engineering_influence.services.typesetting.print_document import PrintDocument
from engineering_influence.services.typesetting.tex_text import TexText

PAYLOAD = r"x}\EIcanary{y"
LIVE = "\\EIcanary"
URL_PAYLOADS = [
    r"https://x.test/}\EIcanary{",
    r"https://x.test/a\EIcanary",
    r"https://x.test/{\EIcanary",
]


def assert_dead(tex: str) -> None:
    assert LIVE not in tex, f"live TeX reached the output:\n{tex}"


def unescaped_braces(tex: str) -> tuple[int, int]:
    """Counts of ``{`` and ``}`` not preceded by a backslash."""
    return len(re.findall(r"(?<!\\){", tex)), len(re.findall(r"(?<!\\)}", tex))


def convert(markdown: str, style: str = "prose") -> str:
    return MarkdownLatexConverter().convert(markdown, style=style)


@pytest.mark.parametrize("style", ["prose", "plain", "references"])
@pytest.mark.parametrize(
    "markdown",
    [
        PAYLOAD,
        f"# not allowed\n\n## {PAYLOAD}\n\ntext",
        f"### {PAYLOAD}\n\ntext",
        f"#### {PAYLOAD}\n\ntext",
        f"*{PAYLOAD}* and **{PAYLOAD}** and ~~{PAYLOAD}~~",
        f"`{PAYLOAD}`",
        f"- {PAYLOAD}\n- second",
        f"1. {PAYLOAD}\n2. second",
        f"> {PAYLOAD}",
        f"| a | b |\n|---|---|\n| {PAYLOAD} | {PAYLOAD} |",
        f"[{PAYLOAD}](https://ok.test)",
        f"[CALLOUT]\n{PAYLOAD}\n[/CALLOUT]",
        f"[ILLUSTRATION]\n{PAYLOAD}\n[/ILLUSTRATION]",
        f"text\n\n<div>{PAYLOAD}</div>\n\nmore",
        f"inline <b>{PAYLOAD}</b> html",
    ],
)
def test_untrusted_markdown_text_is_escaped(markdown: str, style: str) -> None:
    if markdown.startswith("# not allowed"):
        markdown = markdown.split("\n\n", 1)[1]
    assert_dead(convert(markdown, style))


@pytest.mark.parametrize("url", URL_PAYLOADS)
def test_a_bare_url_cannot_close_its_group_or_start_a_macro(url: str) -> None:
    assert_dead(convert(f"See {url} for more."))


@pytest.mark.parametrize("url", URL_PAYLOADS)
def test_a_link_target_cannot_close_its_group_or_start_a_macro(url: str) -> None:
    assert_dead(convert(f"A [link]({url}) here."))


def test_an_encoded_url_has_no_bare_percent_that_would_start_a_tex_comment() -> None:
    tex = convert(r"See https://x.test/}\EIcanary{ and https://x.test/100%25 now.")
    assert not re.search(r"(?<!\\)%", tex)


def test_a_url_keeps_balanced_braces_in_the_output() -> None:
    tex = convert(r"See https://x.test/}\EIcanary{ now.")
    opening, closing = unescaped_braces(tex)
    assert opening == closing


@pytest.mark.parametrize(
    "code",
    [
        "```\n\\end{verbatim}\\EIcanary\n```",
        "```\nline\n\\end{verbatim} \\EIcanary{}\n```",
        "    \\end{verbatim}\\EIcanary",
        "```\n\\end{ verbatim }\\EIcanary\n```",
        "```\n\\end{verbatim*}\\EIcanary\n```",
    ],
)
def test_a_code_block_cannot_end_its_verbatim_environment_early(code: str) -> None:
    with pytest.raises(ManuscriptError, match="verbatim"):
        convert(code)


def test_ordinary_code_still_prints_verbatim_and_unchanged() -> None:
    code = "print('{hi}') # 50% \\ done\n"
    tex = convert(f"```\n{code}```")
    assert f"\\begin{{verbatim}}\n{code}\\end{{verbatim}}" in tex


def chapter(kind: str) -> Chapter:
    return Chapter(
        Path("x.md"),
        kind,
        title=PAYLOAD,
        short=PAYLOAD,
        body=f"{PAYLOAD}\n\n## {PAYLOAD}\n",
        epigraph=(PAYLOAD, PAYLOAD),
        number=3 if kind == "chapter" else None,
    )


@pytest.mark.parametrize("kind", ["front", "chapter", "back"])
@pytest.mark.parametrize("numbered", [True, False])
def test_chapter_titles_running_heads_and_epigraphs_are_escaped(kind: str, numbered: bool) -> None:
    assert_dead(ChapterTex().render(chapter(kind), number_chapters=numbered))


TEXT_FIELDS = (
    "title",
    "subtitle",
    "author",
    "publisher",
    "edition",
    "isbn",
    "ebook_isbn",
    "website",
    "email",
    "dedication",
    "copyright_notes",
    "author_bio",
)


def metadata(field: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "title": "T",
        "author": "A",
        "publisher": "P",
        "edition": "E",
        "author_bio": "Bio.",
        "year": 2030,
    }
    base[field] = PAYLOAD
    return base


def a_book(meta: dict[str, Any]) -> Book:
    return Book(
        "demo",
        meta,
        front=[chapter("front")],
        parts=[(PAYLOAD, [chapter("chapter")])],
        back=[chapter("back")],
    )


@pytest.mark.parametrize("field", TEXT_FIELDS)
def test_every_metadata_field_is_escaped_in_the_print_book(field: str) -> None:
    assert_dead(PrintDocument().render(a_book(metadata(field))))


@pytest.mark.parametrize("field", TEXT_FIELDS)
def test_every_metadata_field_is_escaped_in_the_ebook(field: str) -> None:
    assert_dead(EbookDocument().render(a_book(metadata(field))))


def test_the_also_by_list_is_escaped() -> None:
    meta = {**metadata("edition"), "edition": "E", "also_by": [PAYLOAD, "Fine"]}
    assert_dead(PrintDocument().render(a_book(meta)))
    assert_dead(EbookDocument().render(a_book(meta)))


def test_a_website_with_a_script_scheme_is_refused_in_both_books() -> None:
    meta = {**metadata("website"), "website": "javascript:alert(1)"}
    with pytest.raises(ManuscriptError, match="http or https"):
        PrintDocument().render(a_book(meta))
    with pytest.raises(ManuscriptError, match="http or https"):
        EbookDocument().render(a_book(meta))


def test_character_notation_cannot_smuggle_a_backslash() -> None:
    """``^^5c`` is a backslash to TeX, so a caret must never reach the output unescaped."""
    for tex in (
        convert("^^5cEIcanary and ^^M and ^^^^5c"),
        PrintDocument().render(a_book({**metadata("title"), "title": "^^5cEIcanary"})),
        EbookDocument().render(a_book({**metadata("title"), "title": "^^5cEIcanary"})),
    ):
        assert "^^" not in tex.replace("\\textasciicircum{}", "")
        assert_dead(tex)


@pytest.mark.parametrize("field", ["title", "subtitle", "author", "edition"])
def test_pdf_info_fields_cannot_run_tex_or_break_the_pdf_string(field: str) -> None:
    tex = PrintDocument().render(a_book(metadata(field)))
    info = next(line for line in tex.splitlines() if line.startswith("\\setpdfinfo"))
    assert "\\EIcanary" not in info
    assert info.count("(") == info.count(")") == 0
    assert "EIcanary" in info  # the text survives; only the characters TeX acts on are dropped


def test_an_email_address_is_neutralised_in_the_link_and_in_its_text() -> None:
    meta = {**metadata("email"), "email": r"a}\EIcanary{@x.test"}
    assert_dead(PrintDocument().render(a_book(meta)))
    assert_dead(EbookDocument().render(a_book(meta)))


TEXT = TexText()


@pytest.mark.parametrize(
    ("raw", "safe"),
    [
        ("Plain Title", "Plain Title"),
        ("Q&A: Fear (and Love) $5", "Q&A: Fear (and Love) $5"),
        ("C# in Depth", "C in Depth"),
        ("a) b (c", "a b c"),
        ("a)(b", "ab"),
        ("((a)) (b)", "((a)) (b)"),
        (r"x}\EIcanary{y", "xEIcanaryy"),
        ("line one\nline two\r\tend", "line one line two end"),
        ("^^5c and ~ and 50%", "5c and  and 50"),
        ("nul\x00 del\x7f esc\x1b", "nul del esc"),
        ("caf\u00e9 \u201cquoted\u201d", "caf\u00e9 \u201cquoted\u201d"),
        ("", ""),
    ],
)
def test_pdf_info_drops_only_what_tex_or_pdf_would_act_on(raw: str, safe: str) -> None:
    assert TEXT.pdf_info(raw) == safe


@pytest.mark.parametrize(
    ("raw", "safe"),
    [
        ("https://x.test/a?b=c&d=e", "https://x.test/a?b=c&d=e"),
        ("  https://x.test  ", "https://x.test"),
        ("https://x.test/50%", r"https://x.test/50\%"),
        ("https://x.test/#top", r"https://x.test/\#top"),
        (r"https://x.test/}\y{", r"https://x.test/\%7D\%5Cy\%7B"),
    ],
)
def test_url_encodes_braces_and_backslashes_and_escapes_percent_and_hash(
    raw: str, safe: str
) -> None:
    assert TEXT.url(raw) == safe


@pytest.mark.parametrize(
    "address",
    [
        "https://pub.example",
        "HTTP://pub.example",
        "pub.example",
        "www.pub.example/x",
        "pub.example:8080/x",
        "pub.example:8080",
    ],
)
def test_a_web_address_with_no_scheme_or_an_http_one_is_accepted(address: str) -> None:
    assert TEXT.web_url(address) == TEXT.url(address)


@pytest.mark.parametrize(
    "address",
    [
        "javascript:alert(1)",
        "JavaScript:alert(1)",
        "  javascript:alert(1)",
        "data:text/html,x",
        "file:///etc/passwd",
        "mailto:a@b.test",
        "vbscript:x",
        "ftp://x.test",
    ],
)
def test_a_web_address_with_any_other_scheme_is_refused(address: str) -> None:
    with pytest.raises(ManuscriptError, match="http or https"):
        TEXT.web_url(address)
