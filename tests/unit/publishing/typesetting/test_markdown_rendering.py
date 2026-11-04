"""Markdown to LaTeX rendering: escaping, inline, blocks, tables, openings, converter."""

import pytest
from markdown_it.token import Token

from engineering_influence.publishing.typesetting.block_renderer import BlockRenderer
from engineering_influence.publishing.typesetting.inline_renderer import InlineRenderer
from engineering_influence.publishing.typesetting.latex_escaper import LatexEscaper
from engineering_influence.publishing.typesetting.latex_table import LatexTable
from engineering_influence.publishing.typesetting.manuscript_error import ManuscriptError
from engineering_influence.publishing.typesetting.markdown_latex_converter import (
    MarkdownLatexConverter,
)
from engineering_influence.publishing.typesetting.markdown_parser import MarkdownParser
from engineering_influence.publishing.typesetting.opening_formatter import OpeningFormatter

PARSER = MarkdownParser()


def inline(markdown: str) -> str:
    return InlineRenderer().inline(PARSER.parse_inline(markdown)[0].children or [])


def blocks(markdown: str, style: str = "plain") -> str:
    return BlockRenderer(style).render(PARSER.parse(markdown))


def test_escaper_handles_specials_spaces_and_ellipses() -> None:
    escaped = LatexEscaper().escape("50% of $5 & #1_x ^ ~ \\ {a} <b> see Chapter 7, p. 12... ok")
    assert escaped == (
        r"50\% of \$5 \& \#1\_x \textasciicircum{} \textasciitilde{} \textbackslash{} "
        r"\{a\} \textless{}b\textgreater{} see Chapter~7, p.~12\dots{} ok"
    )


def test_inline_formatting() -> None:
    result = inline("*em* **strong** ~~gone~~ `a_b` line  \nnext\nsoft")
    assert result == r"\emph{em} \textbf{strong} \sout{gone} \texttt{a\_b} line\\" + "\nnext soft"


def test_straight_quotes_are_curled_by_position() -> None:
    assert InlineRenderer().text('He said "hi" and (\u201cx") y') == (
        "He said \u201chi\u201d and (\u201cx\u201d) y"
    )


def test_bare_urls_become_breakable_url_commands() -> None:
    result = InlineRenderer().text("See https://e.example/a%20b#c, then go.")
    assert result == r"See \url{https://e.example/a\%20b\#c}, then go."


def test_links_footnote_only_http_targets() -> None:
    assert inline("[site](https://e.example/x#y)") == (
        r"{site}\footnote{\url{https://e.example/x\#y}}"
    )
    assert inline("[mail](mailto:a@b.c)") == "{mail}"
    assert inline("[empty]()") == "{empty}"


def test_link_without_href_attribute_has_no_footnote() -> None:
    renderer = InlineRenderer()
    tokens = [Token("link_open", "a", 1), Token("link_close", "a", -1)]
    assert renderer.inline(tokens) == "{}"


def test_inline_html_is_dropped_and_images_are_rejected() -> None:
    assert inline("a <b>x</b>") == "a x"
    with pytest.raises(ManuscriptError, match="images"):
        inline("![alt](pic.png)")


def test_unknown_inline_token_is_rejected() -> None:
    with pytest.raises(ManuscriptError, match="unhandled inline token mystery"):
        InlineRenderer().inline([Token("mystery", "", 0)])


def test_opening_sets_drop_cap_and_lead_words() -> None:
    assert OpeningFormatter().format("Where the road ends, we begin.") == (
        r"\opening{W}{here the road}" + " ends, we begin."
    )
    assert OpeningFormatter().format("Stop now, then go on.") == (
        r"\opening{S}{top now,}" + " then go on."
    )
    assert OpeningFormatter().format("Stop. Then go on.") == r"\noindent Stop. Then go on."


def test_opening_lead_stops_at_commands_and_short_paragraphs() -> None:
    assert OpeningFormatter().format(r"Once \emph{upon} a time") == (
        r"\opening{O}{nce}" + r" \emph{upon} a time"
    )
    assert OpeningFormatter().format("Go") == r"\noindent Go"
    assert OpeningFormatter().format("lowercase start") == r"\noindent lowercase start"


def test_opening_can_fall_back_below_a_minimum_length() -> None:
    assert OpeningFormatter(min_chars=100).format("Once upon a time") == (
        r"\noindent{\capsfont Once upon a}" + " time"
    )


def test_table_pads_short_rows_and_bolds_the_header() -> None:
    table = LatexTable().render([["A", "B"], ["1"]])
    assert r"\textbf{A} & \textbf{B} \\" in table and "1 &  \\\\" in table
    assert r"\midrule" in table and table.count("\\toprule") == 1
    assert LatexTable().render([]) == ""


def test_headings_and_the_single_level_one_rule() -> None:
    result = blocks("## Two\n\n### Three\n\n#### Four")
    assert result == (
        "\n\\booksection{Two}\n\n\\booksubsection{Three}\n\n\\booksubsubsection{Four}\n"
    )
    with pytest.raises(ManuscriptError, match="only one level-1"):
        blocks("# One")


def test_prose_style_opens_first_paragraph_only() -> None:
    result = blocks("Where it begins.\n\nSecond one.", style="prose")
    assert result.startswith("\n\\opening{W}{here it begins.}")
    assert result.count(r"\opening") == 1 and "\nSecond one.\n" in result


def test_quote_and_heading_do_not_take_the_opening() -> None:
    assert (
        r"\opening"
        not in blocks("> Quoted first.\n\nThen prose.", style="prose").split("end{quote}")[0]
    )
    assert r"\opening" not in blocks("## Head\n\nAfter head.", style="prose")


def test_reference_style_wraps_entries() -> None:
    assert blocks("Ref one.", style="references") == "\n\\refentry{Ref one.}\n"


def test_lists_quotes_code_and_ignored_blocks() -> None:
    result = blocks(
        "- a\n- b\n\n3. c\n\nbetween\n\n1. d\n\n> q\n\n```\ncode\n```\n\n---\n\n<div>x</div>\n"
    )
    assert "\\begin{itemize}\n\\item a\n\\item b\n\\end{itemize}" in result
    assert "\\begin{enumerate}[start=3]\n\\item c\n\\end{enumerate}" in result
    assert "\\begin{enumerate}\n\\item d" in result
    assert "\\begin{quote}\n\nq\n\\end{quote}" in result
    assert "\\begin{verbatim}\ncode\n\\end{verbatim}" in result
    assert "div" not in result


def test_indented_code_block_is_verbatim() -> None:
    assert "\\begin{verbatim}\nplain\n\\end{verbatim}" in blocks("para\n\n    plain\n")


def test_tables_render_through_the_block_renderer() -> None:
    result = blocks("| H1 | H2 |\n| --- | --- |\n| a | b |\n")
    assert r"\textbf{H1} & \textbf{H2}" in result and "a & b" in result


def test_unknown_block_token_is_rejected() -> None:
    with pytest.raises(ManuscriptError, match="unhandled block token mystery"):
        BlockRenderer().render([Token("mystery", "", 0)])


def test_converter_wraps_callouts_illustrations_and_references() -> None:
    body = "Lead in.\n\n[CALLOUT]\nInside the callout.\n[/CALLOUT]\n\nMiddle.\n\n[ILLUSTRATION]\nA figure.\n[/ILLUSTRATION]\n\nEnd."
    result = MarkdownLatexConverter().convert(body, style="prose")
    assert "\\begin{callout}\nInside the callout.\n\\end{callout}" in result
    assert "\\begin{illustration}\nA figure.\n\\end{illustration}" in result
    assert result.count(r"\opening") == 1 and "\nMiddle.\n" in result
    wrapped = MarkdownLatexConverter().convert("One.", style="references")
    assert wrapped.startswith("\\begin{referencelist}\n") and wrapped.endswith(
        "\\end{referencelist}\n"
    )
