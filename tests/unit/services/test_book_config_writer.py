# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""BookConfigWriter: the listing, the author's details and the chapters as TOML a loader reads back exactly."""

import tomllib

from hypothesis import assume, given
from hypothesis import strategies as st

from engineering_influence.models.author_profile import AuthorProfile
from engineering_influence.models.book_metadata import BookMetadata
from engineering_influence.services.book_config_writer import BookConfigWriter
from engineering_influence.services.interfaces.book_config_writer_interface import (
    BookConfigWriterInterface,
)

WRITER = BookConfigWriter()
DESCRIPTION = " ".join(["Bees are easier to keep than most people think."] * 10)
KEYWORDS = tuple(f"keyword {n}" for n in range(7))


def metadata(**changes: object) -> BookMetadata:
    fields: dict[str, object] = {
        "title": "Hive Mind",
        "subtitle": "A calm guide",
        "description": DESCRIPTION,
        "keywords": KEYWORDS,
        "categories": ("Books > Science & Math", "Books > Crafts > Bees"),
    }
    return BookMetadata(**{**fields, **changes})  # type: ignore[arg-type]


def profile(**changes: object) -> AuthorProfile:
    fields: dict[str, object] = {
        "author": "Ann Author",
        "publisher": "Pub House",
        "edition": "First Edition",
        "author_bio": "Ann writes.\n\nAnd more.",
    }
    return AuthorProfile(**{**fields, **changes})  # type: ignore[arg-type]


def test_it_is_a_book_config_writer() -> None:
    assert isinstance(WRITER, BookConfigWriterInterface)


def test_the_config_has_the_listing_the_release_contract_and_one_part_of_chapters() -> None:
    assert WRITER.write(
        "nonfiction", metadata(), None, None, ("chapter_01.md", "chapter_02.md")
    ) == (
        'kind = "nonfiction"\n'
        'title = "Hive Mind"\n'
        'subtitle = "A calm guide"\n'
        f'description = "{DESCRIPTION}"\n'
        'source = "src"\n'
        "\n"
        "[release]\n"
        'keywords = ["keyword 0", "keyword 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5", "keyword 6"]\n'
        'categories = ["Books > Science & Math", "Books > Crafts > Bees"]\n'
        "\n"
        "[[parts]]\n"
        'title = "Part One"\n'
        "chapters = [\n"
        '  "chapter_01.md",\n'
        '  "chapter_02.md",\n'
        "]\n"
    )


def test_the_author_profile_is_written_between_the_source_and_the_release_table() -> None:
    text = WRITER.write(
        "nonfiction",
        metadata(),
        profile(year=2031, also_by=("Earlier Book", "Another")),
        "5.5x8.5",
        ("a.md",),
    )
    config = tomllib.loads(text)
    assert (config["author"], config["publisher"], config["edition"]) == (
        "Ann Author",
        "Pub House",
        "First Edition",
    )
    assert (config["year"], config["author_bio"]) == (2031, "Ann writes.\n\nAnd more.")
    assert config["also_by"] == ["Earlier Book", "Another"]
    assert config["trim_size"] == "5.5x8.5"
    assert text.index('trim_size = "5.5x8.5"') < text.index("author = ") < text.index("[release]")


def test_without_a_profile_it_does_not_invent_what_only_the_author_can_say() -> None:
    config = tomllib.loads(WRITER.write("nonfiction", metadata(), None, None, ("a.md",)))
    assert set(config) == {"kind", "title", "subtitle", "description", "source", "release", "parts"}
    assert config["release"] == {
        "keywords": list(KEYWORDS),
        "categories": ["Books > Science & Math", "Books > Crafts > Bees"],
    }


def test_a_trim_size_is_written_only_when_there_is_one() -> None:
    assert 'trim_size = "5x8"\n' in WRITER.write("nonfiction", metadata(), None, "5x8", ("a.md",))
    for none in (None, ""):
        assert "trim_size" not in WRITER.write("nonfiction", metadata(), None, none, ("a.md",))


def test_a_value_with_quotes_backslashes_and_a_delete_character_reads_back_the_same() -> None:
    title = 'The "Hive" \\ and a caf\u00e9 ' + chr(0x7F) + " end"
    parts = tomllib.loads(
        WRITER.write(
            "nonfiction", metadata(title=title.replace(chr(0x7F), "x")), None, None, ("a.md",)
        )
    )
    assert parts["title"] == title.replace(chr(0x7F), "x")
    written = WRITER._text("a" + chr(0x7F) + "b")
    assert tomllib.loads(f"v = {written}")["v"] == "a" + chr(0x7F) + "b"


line = st.text(
    alphabet=st.characters(
        codec="utf-8", blacklist_categories=("Cc", "Cf", "Zl", "Zp", "Co", "Cn")
    ),
    min_size=1,
    max_size=40,
).filter(lambda text: text == text.strip())


@given(
    author=line,
    publisher=line,
    bio=st.text(
        alphabet=st.characters(
            codec="utf-8", blacklist_categories=("Cc", "Cf", "Zl", "Zp", "Co", "Cn")
        ),
        min_size=1,
        max_size=200,
    ),
    titles=st.lists(line, max_size=4),
    year=st.none() | st.integers(1000, 9999),
)
def test_any_valid_profile_reads_back_exactly(
    author: str, publisher: str, bio: str, titles: list[str], year: int | None
) -> None:
    assume(bio.strip())
    made = profile(
        author=author, publisher=publisher, author_bio=bio, also_by=tuple(titles), year=year
    )
    config = tomllib.loads(WRITER.write("nonfiction", metadata(), made, None, ("a.md",)))
    for key, value in made.entries().items():
        assert config[key] == value


def test_the_authors_pricing_is_written_as_the_release_pricing_table() -> None:
    from engineering_influence.models.book_pricing import BookPricing

    prices = BookPricing("2026-11-19", "https://kdp.example/costs", 4.99, 12, 22.99)
    text = WRITER.write("novel", metadata(), profile(pricing=prices), None, ("a.md",))
    config = tomllib.loads(text)
    assert config["release"]["pricing"] == {
        "verified_on": "2026-11-19",
        "source_url": "https://kdp.example/costs",
        "ebook": 4.99,
        "paperback": 12,
        "hardcover": 22.99,
    }
    assert config["release"]["keywords"] and config["parts"][0]["chapters"] == ["a.md"]
    assert config["release"]["formats"] == {"kdp_hardcover": True}
    assert config["formats"] == {"hardcover": True}
    assert text.index("[release]") < text.index("[release.pricing]") < text.index("[[parts]]")


def test_without_pricing_there_is_no_pricing_table() -> None:
    config = tomllib.loads(WRITER.write("novel", metadata(), profile(), None, ("a.md",)))
    assert "pricing" not in config["release"]


def test_a_book_with_no_hardcover_price_is_not_a_hardcover() -> None:
    from engineering_influence.models.book_pricing import BookPricing

    prices = BookPricing("2026-11-19", "https://kdp.example/costs", 4.99, 12.99)
    config = tomllib.loads(
        WRITER.write("novel", metadata(), profile(pricing=prices), None, ("a.md",))
    )
    assert "formats" not in config and "formats" not in config["release"]
    assert "hardcover" not in config["release"]["pricing"]
