# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SkillMarkdownParser: a SKILL.md becomes a name, a description and sections, and anything unclear is refused."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.services.interfaces.skill_markdown_parser_interface import (
    SkillMarkdownParserInterface,
)
from engineering_influence.services.skill_markdown_parser import SkillMarkdownParser

PARSER = SkillMarkdownParser()
SAMPLE = """---
name: research-methodology
description: "Comprehensive research methodology reference. Use when helping with papers."
domains: [research, writing]
allowed-tools: Read, Grep
phases:
  - plan
  - write
---

# Research Methodology Reference Guide

A paragraph before any section.

## Source Evaluation

Use CRAAP and SIFT.

```bash
## this is not a heading
echo hi
```

## Database Searching

Use Boolean operators.

## Empty Section

## Source Evaluation

A second one with the same title.
"""


def invalid(text: str) -> str:
    with pytest.raises(ApplicationError) as error:
        PARSER.parse(text)
    assert (error.value.code, error.value.http_status) == ("SKILL_MARKDOWN_INVALID", 422)
    assert error.value.message.startswith("the skill file cannot be read: ")
    return error.value.message.removeprefix("the skill file cannot be read: ")


def small(body: str, name: str = "a", description: str = "d") -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n{body}"


def test_it_is_a_skill_markdown_parser() -> None:
    assert isinstance(PARSER, SkillMarkdownParserInterface)


def test_a_real_shaped_file_gives_its_name_description_and_sections() -> None:
    made = PARSER.parse(SAMPLE)
    assert made.name == "research-methodology"
    assert (
        made.description
        == "Comprehensive research methodology reference. Use when helping with papers."
    )
    assert made.titles() == (
        "Overview",
        "Source Evaluation",
        "Database Searching",
        "Source Evaluation (2)",
    )
    assert made.section("Overview") == "A paragraph before any section."


def test_other_frontmatter_keys_are_set_aside_and_named_in_order() -> None:
    assert PARSER.parse(SAMPLE).ignored == ("allowed-tools", "domains", "phases")


def test_a_heading_inside_a_code_fence_is_not_a_heading() -> None:
    body = PARSER.parse(SAMPLE).section("Source Evaluation")
    assert body is not None and "## this is not a heading" in body and "echo hi" in body


def test_a_heading_with_no_text_is_dropped_and_repeated_titles_are_numbered() -> None:
    made = PARSER.parse(SAMPLE)
    assert "Empty Section" not in made.titles()
    assert made.section("Source Evaluation (2)") == "A second one with the same title."


def test_a_tilde_fence_works_too_and_closing_hashes_are_taken_off_a_title() -> None:
    made = PARSER.parse(small("## Title ##\n~~~\n## no\n~~~\n"))
    assert made.titles() == ("Title",)
    assert made.section("Title") == "~~~\n## no\n~~~"


def test_text_before_the_first_section_is_overview_without_the_title_line() -> None:
    made = PARSER.parse(small("# The Title\n\nIntro.\n\n## One\n\nBody."))
    assert made.section("Overview") == "Intro."
    assert PARSER.parse(small("# The Title\n\n## One\n\nBody.")).titles() == ("One",)


def test_a_second_level_one_heading_is_kept_as_text() -> None:
    made = PARSER.parse(small("# First\n\n# Second\n\ntext"))
    assert made.section("Overview") == "# Second\n\ntext"


@pytest.mark.parametrize(
    ("raw", "value"),
    [
        ('"quoted, with: colon"', "quoted, with: colon"),
        ("'single ''quoted'''", "single 'quoted'"),
        (r'"escaped \"quote\" and \\ slash"', 'escaped "quote" and \\ slash'),
        ("plain words", "plain words"),
        (r'"broken \q escape"', r"broken \q escape"),
    ],
)
def test_a_description_may_be_quoted_in_either_style_or_plain(raw: str, value: str) -> None:
    assert PARSER.parse(small("text", description=raw)).description == value


def test_a_description_is_made_one_line_with_single_spaces() -> None:
    assert PARSER.parse(small("text", description="'  spaced   out  '")).description == "spaced out"


def test_windows_line_endings_and_a_byte_order_mark_are_fine() -> None:
    text = chr(0xFEFF) + "---\r\nname: a\r\ndescription: d\r\n---\r\n## One\r\n\r\nBody\r\n"
    assert PARSER.parse(text).section("One") == "Body"


def test_a_file_must_start_with_frontmatter_and_close_it() -> None:
    assert invalid("# Just markdown") == "it does not start with a --- frontmatter block"
    assert invalid("") == "it does not start with a --- frontmatter block"
    assert (
        invalid("---\nname: a\ndescription: d\n")
        == "its frontmatter block is never closed with ---"
    )


@pytest.mark.parametrize("key", ["name", "description"])
def test_the_name_and_description_are_required(key: str) -> None:
    other = "description: d" if key == "name" else "name: a"
    assert invalid(f"---\n{other}\n---\ntext") == f"the frontmatter has no {key}"


@pytest.mark.parametrize("scalar", ["|", ">", "|-", ">-", "|+", ">+"])
def test_a_description_in_a_block_scalar_is_refused(scalar: str) -> None:
    text = f"---\nname: a\ndescription: {scalar}\n  two lines\n  of text\n---\ntext"
    assert invalid(text) == "the description runs over more than one line; put it on one line"


def test_a_name_that_continues_on_the_next_line_is_refused() -> None:
    text = "---\nname: a\n  more\ndescription: d\n---\ntext"
    assert invalid(text) == "the name runs over more than one line; put it on one line"


def test_a_frontmatter_line_that_is_not_a_key_and_a_repeated_key_are_refused() -> None:
    assert invalid("---\nname: a\njust some words\n---\ntext") == (
        "the frontmatter line 'just some words' is not 'key: value'"
    )
    assert invalid("---\nname: a\nname: b\ndescription: d\n---\ntext") == (
        "the frontmatter has 'name' twice"
    )


def test_a_list_under_a_set_aside_key_may_start_at_the_margin() -> None:
    made = PARSER.parse(
        small("text").replace("description: d", "description: d\nphases:\n- plan\n- write")
    )
    assert made.ignored == ("phases",)
    assert made.description == "d"


def test_a_block_scalar_marker_with_nothing_after_it_is_still_refused() -> None:
    text = "---\nname: a\ndescription: >\n---\ntext"
    assert invalid(text) == "the description runs over more than one line; put it on one line"


def test_blank_lines_in_the_frontmatter_are_fine() -> None:
    assert PARSER.parse("---\nname: a\n\ndescription: d\n\n---\ntext").name == "a"


def test_a_file_with_no_text_after_the_frontmatter_is_refused() -> None:
    assert invalid(small("\n  \n")) == "it has no text after the frontmatter"
    assert invalid(small("## Empty\n")) == "it has no text after the frontmatter"


def test_an_empty_name_value_is_refused_with_the_models_reason() -> None:
    assert (
        invalid("---\nname:\ndescription: d\n---\ntext") == "a skill document has a one-line name"
    )


@given(st.text())
def test_any_text_is_a_document_or_a_refusal_and_never_another_error(text: str) -> None:
    try:
        made = PARSER.parse(text)
    except ApplicationError as error:
        assert error.code == "SKILL_MARKDOWN_INVALID"
    else:
        assert made.titles() and made.name and made.description
