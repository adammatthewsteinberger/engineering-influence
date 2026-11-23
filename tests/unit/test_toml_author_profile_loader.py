# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""TomlAuthorProfileLoader: a profile file is read strictly, and a bad one says why."""

from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.author.toml_author_profile_loader import (
    TomlAuthorProfileLoader,
)
from engineering_influence.interfaces.author_profile_loader_interface import (
    AuthorProfileLoaderInterface,
)

GOOD = """author = "Ann Author"
publisher = "Pub House"
edition = "First Edition"
author_bio = "Ann writes.\\n\\nAnd more."
year = 2031
website = "https://pub.example"
also_by = ["Earlier Book"]
"""
LOADER = TomlAuthorProfileLoader()


def write(tmp_path: Path, text: str | bytes) -> Path:
    path = tmp_path / "author.toml"
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


def refused(path: Path) -> str:
    with pytest.raises(ApplicationError) as error:
        LOADER.load(path)
    assert (error.value.code, error.value.http_status) == ("AUTHOR_PROFILE_INVALID", 503)
    assert error.value.message.startswith(f"the author profile {path} cannot be used: ")
    return error.value.message.removeprefix(f"the author profile {path} cannot be used: ")


def test_it_is_an_author_profile_loader() -> None:
    assert isinstance(LOADER, AuthorProfileLoaderInterface)


def test_a_good_file_is_read_into_a_profile(tmp_path: Path) -> None:
    profile = LOADER.load(write(tmp_path, GOOD))
    assert profile is not None
    assert (profile.author, profile.publisher, profile.edition) == (
        "Ann Author",
        "Pub House",
        "First Edition",
    )
    assert profile.author_bio == "Ann writes.\n\nAnd more."
    assert (profile.year, profile.website, profile.also_by) == (
        2031,
        "https://pub.example",
        ("Earlier Book",),
    )


def test_a_file_that_is_not_there_is_none(tmp_path: Path) -> None:
    assert LOADER.load(tmp_path / "missing.toml") is None
    assert LOADER.load(tmp_path) is None


def test_a_file_that_is_not_toml_or_not_utf8_is_refused(tmp_path: Path) -> None:
    assert "not valid UTF-8 TOML" in refused(write(tmp_path, "author = "))
    assert "not valid UTF-8 TOML" in refused(write(tmp_path, b"author = \xff\xfe"))


def test_a_file_over_sixty_four_kib_is_refused_unread(tmp_path: Path) -> None:
    assert refused(write(tmp_path, "#" * (64 * 1024 + 1))) == "it is larger than 65536 bytes"
    LOADER.load(write(tmp_path, GOOD + "#" * 1000))
    exactly = GOOD + "#" * (64 * 1024 - len(GOOD.encode()))
    assert len(exactly.encode()) == 64 * 1024
    assert LOADER.load(write(tmp_path, exactly)) is not None


def test_an_unknown_key_is_refused_and_named(tmp_path: Path) -> None:
    assert refused(write(tmp_path, GOOD + 'publiser = "x"\n')) == "it has unknown keys ['publiser']"


@pytest.mark.parametrize("key", ["author", "publisher", "edition", "author_bio", "website"])
def test_a_text_value_that_is_not_text_is_refused(tmp_path: Path, key: str) -> None:
    text = "\n".join(line for line in GOOD.splitlines() if not line.startswith(key + " "))
    assert refused(write(tmp_path, text + f"\n{key} = 3\n")) == f"{key} is text"


def test_year_and_also_by_must_be_the_right_kind(tmp_path: Path) -> None:
    base = "\n".join(line for line in GOOD.splitlines() if not line.startswith(("year", "also_by")))
    assert refused(write(tmp_path, base + '\nyear = "2031"\n')) == "year is a whole number"
    assert refused(write(tmp_path, base + "\nyear = true\n")) == "year is a whole number"
    assert refused(write(tmp_path, base + '\nalso_by = "one"\n')) == "also_by is a list of titles"
    assert refused(write(tmp_path, base + "\nalso_by = [1]\n")) == "also_by is a list of titles"


def test_what_the_profile_model_refuses_is_refused_with_its_reason(tmp_path: Path) -> None:
    assert refused(write(tmp_path, GOOD.replace("First Edition", "First printing"))) == (
        "the edition has to say 'Edition', as in 'First Edition'"
    )
    assert "publisher" in refused(write(tmp_path, 'author = "A"\n'))
