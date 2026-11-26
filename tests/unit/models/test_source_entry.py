# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SourceEntry: numbered from 1, named as an artifact, pinned by a 64-character digest."""

import pytest

from engineering_influence.models.source_entry import SourceEntry

DIGEST = "a" * 64


def test_an_entry_is_named_as_its_artifact() -> None:
    assert SourceEntry(7, "text", DIGEST).artifact() == "source/007.md"


def test_entries_are_numbered_from_one() -> None:
    with pytest.raises(ValueError, match="numbered from 1"):
        SourceEntry(0, "text", DIGEST)


def test_a_digest_is_a_sha256_hex_string() -> None:
    with pytest.raises(ValueError, match="64-character SHA-256"):
        SourceEntry(1, "text", "short")
