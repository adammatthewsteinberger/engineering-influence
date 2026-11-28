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
from hypothesis import given
from hypothesis import strategies as st

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
    "https://x.test/^^5cEIcanary",
    "https://x.test/^^^^5cEIcanary",
    'https://x.test/"onmouseover="EICANARY',
]


def assert_dead(tex: str) -> None:
    assert LIVE not in tex, f"live TeX reached the output:\n{tex}"
    # TeX reads "^^5c" as a backslash, so the macro only becomes live when TeX tokenizes it.
    assert "^^" not in tex.replace("\\textasciicircum{}", ""), f"notation survived:\n{tex}"


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


@pytest.mark.parametrize(
    "template",
    [
        "## see {url}",
        "*{url}*",
        "**{url}**",
        "- {url}",
        "> {url}",
        "| a | b |\n|---|---|\n| {url} | x |",
        "[label]({url})",
        "[*{url}*]({url})",
    ],
)
@pytest.mark.parametrize("url", ["https://x.test/^^5cEIcanary", "https://x.test/}\\EIcanary{"])
def test_a_url_is_dead_wherever_it_sits_in_a_macro_argument(template: str, url: str) -> None:
    """Emphasis, headings, table cells and footnotes are all macro arguments, tokenized early."""
    assert_dead(convert(template.format(url=url)))


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
    # A website must at least look like a web address, so it carries the payload after a scheme.
    base[field] = "https://x.test/" + PAYLOAD if field == "website" else PAYLOAD
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
        ("https://x.test/my_page~user", "https://x.test/my_page~user"),
        ("  https://x.test  ", "https://x.test"),
        ("https://x.test/50%", r"https://x.test/50\%"),
        ("https://x.test/#top", r"https://x.test/\#top"),
        (r"https://x.test/}\y{", r"https://x.test/\%7D\%5Cy\%7B"),
        ("https://x.test/^^5c", r"https://x.test/\%5E\%5E5c"),
        ("https://x.test/a\"b'c<d>e f", r"https://x.test/a\%22b\%27c\%3Cd\%3Ee\%20f"),
        ("https://x.test/$5|x`y", r"https://x.test/\%245\%7Cx\%60y"),
        ("https://x.test/caf\u00e9", r"https://x.test/caf\%C3\%A9"),
        ("https://x.test/a\x01b\tc", r"https://x.test/a\%01b\%09c"),
    ],
)
def test_url_becomes_a_valid_uri_with_percent_and_hash_escaped_for_tex(raw: str, safe: str) -> None:
    assert TEXT.url(raw) == safe


@given(st.text())
def test_a_url_can_only_ever_contain_characters_that_are_inert_in_tex_and_html(raw: str) -> None:
    out = TEXT.url(raw)
    # "\\%" and "\\#" are the only backslashes allowed; once they go, only plain URL characters remain.
    plain = out.replace("\\%", "").replace("\\#", "")
    assert re.fullmatch(r"[A-Za-z0-9\-._~:/?\[\]@!&()*+,;=]*", plain), out


def test_surrounding_space_is_ignored_in_a_web_address() -> None:
    assert TEXT.web_url("  https://pub.example \n") == "https://pub.example"


@pytest.mark.parametrize(
    "address",
    [
        "https://pub.example",
        "HTTP://pub.example",
        "https://pub.example:8080/x",
        "pub.example",
        "www.pub.example/about",
        "pub.example/a:b",
        "pub.example?x=1",
    ],
)
def test_an_http_address_or_a_bare_host_is_accepted(address: str) -> None:
    assert TEXT.web_url(address) == TEXT.url(address)


@pytest.mark.parametrize(
    "address",
    [
        "javascript:alert(1)",
        "JavaScript:alert(1)",
        "  javascript:alert(1)",
        "javascript:0/alert(1)",
        "javascript:1",
        "java\tscript:alert(1)",
        "java\nscript:alert(1)",
        "\x01javascript:alert(1)",
        "http://x.test\njavascript:alert(1)",
        "data:text/html,x",
        "file:///etc/passwd",
        "mailto:a@b.test",
        "vbscript:x",
        "ftp://x.test",
        "pub.example:8080",
        "pub.example:8080/x",
        "pub.example/a b",
        "pub.example/a\nb",
        "pub.example?x=1 2",
        "a b",
        "https://",
        "",
        "   ",
    ],
)
def test_anything_else_is_refused_including_every_script_url_and_host_port(address: str) -> None:
    with pytest.raises(ManuscriptError, match="http or https"):
        TEXT.web_url(address)


def test_every_metadata_key_the_documents_read_is_escaped_text_or_reviewed_as_not_text() -> None:
    """A key a document reads is either passed through TexText, or named in NOT_TEXT by a person who checked it.

    A new key that is read but missing from both lists fails here, so it cannot reach the TeX unescaped by accident.
    """
    root = Path(__file__).resolve().parents[4] / "src/engineering_influence/services/typesetting"
    read: set[str] = set()
    for module in ("print_document.py", "ebook_document.py"):
        read |= set(
            re.findall(r'\bm(?:\.get\(|\[)"(\w+)"', (root / module).read_text(encoding="utf-8"))
        )
    NOT_TEXT = {"year", "number_chapters", "kind", "trim_size", "also_by"}
    assert read - set(TEXT_FIELDS) - NOT_TEXT == set()
