# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""BookConfigWriter: the known fields as TOML a loader reads back exactly."""

import tomllib

from hypothesis import given
from hypothesis import strategies as st

from engineering_influence.services.book_config_writer import BookConfigWriter
from engineering_influence.services.interfaces.book_config_writer_interface import (
    BookConfigWriterInterface,
)

WRITER = BookConfigWriter()


def test_it_is_a_book_config_writer() -> None:
    assert isinstance(WRITER, BookConfigWriterInterface)


def test_the_config_names_the_kind_title_source_and_one_part_of_chapters() -> None:
    assert WRITER.write("nonfiction", "Hive Mind", None, ("chapter_01.md", "chapter_02.md")) == (
        'kind = "nonfiction"\n'
        'title = "Hive Mind"\n'
        'source = "src"\n'
        "\n"
        "[[parts]]\n"
        'title = "Part One"\n'
        "chapters = [\n"
        '  "chapter_01.md",\n'
        '  "chapter_02.md",\n'
        "]\n"
    )


def test_a_trim_size_is_written_only_when_there_is_one() -> None:
    with_trim = WRITER.write("nonfiction", "T", "5.5x8.5", ("a.md",))
    assert 'trim_size = "5.5x8.5"\n' in with_trim
    assert "trim_size" not in WRITER.write("nonfiction", "T", None, ("a.md",))
    assert "trim_size" not in WRITER.write("nonfiction", "T", "", ("a.md",))


def test_it_does_not_invent_what_only_the_author_can_say() -> None:
    config = tomllib.loads(WRITER.write("nonfiction", "T", None, ("a.md",)))
    assert set(config) == {"kind", "title", "source", "parts"}


def test_a_title_with_a_delete_character_reads_back_the_same() -> None:
    title = "before" + chr(0x7F) + "after"
    assert tomllib.loads(WRITER.write("nonfiction", title, None, ("a.md",)))["title"] == title


def test_a_title_with_quotes_and_backslashes_reads_back_the_same() -> None:
    title = 'The "Hive" \\ and a caf\u00e9\ttab'
    assert tomllib.loads(WRITER.write("nonfiction", title, None, ("a.md",)))["title"] == title


@given(
    st.text(min_size=1, max_size=120),
    st.lists(st.from_regex(r"[a-z0-9_]{1,12}\.md", fullmatch=True), min_size=1, max_size=5),
)
def test_any_title_and_chapter_list_read_back_exactly(title: str, names: list[str]) -> None:
    config = tomllib.loads(WRITER.write("novel", title, "6x9", tuple(names)))
    assert config["title"] == title
    assert config["parts"] == [{"title": "Part One", "chapters": names}]
    assert (config["kind"], config["trim_size"], config["source"]) == ("novel", "6x9", "src")
