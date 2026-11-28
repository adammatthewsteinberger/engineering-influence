# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""BundledScripture: the six bundled translations, read offline, with verses a translation lacks reported as absent."""

from pathlib import Path

import pytest

from engineering_influence.infrastructure.bundled_scripture import BundledScripture
from engineering_influence.interfaces.scripture_index_interface import ScriptureIndexInterface
from engineering_influence.models.verse_ref import VerseRef


def test_it_is_a_scripture_index_with_the_six_translations() -> None:
    scripture = BundledScripture()
    assert isinstance(scripture, ScriptureIndexInterface)
    assert scripture.translations() == ("asv", "bsb", "dra", "kjv", "web", "ylt")


def test_a_verse_is_read_from_its_translation() -> None:
    scripture = BundledScripture()
    john = (VerseRef("JHN", 3, 16),)
    assert scripture.text("kjv", john) == (
        "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him "
        "should not perish, but have everlasting life."
    )
    assert "only born Son" in (scripture.text("web", john) or "")


def test_a_range_is_joined_in_order_with_a_space() -> None:
    text = BundledScripture().text("kjv", (VerseRef("GEN", 1, 1), VerseRef("GEN", 1, 2)))
    assert text is not None and text.startswith(
        "In the beginning God created the heaven and the earth. "
    )
    assert "And the earth was without form" in text


def test_a_verse_the_translation_leaves_out_is_none() -> None:
    assert BundledScripture().text("bsb", (VerseRef("MRK", 9, 44),)) is None
    assert BundledScripture().text("kjv", (VerseRef("MRK", 9, 44),)) is not None


def test_no_verses_is_no_text() -> None:
    assert BundledScripture().text("kjv", ()) is None


def test_an_unknown_translation_is_refused() -> None:
    with pytest.raises(ValueError, match="not a bundled translation"):
        BundledScripture().text("niv", (VerseRef("JHN", 3, 16),))


def test_a_folder_of_other_texts_reads_its_own_files(tmp_path: Path) -> None:
    import gzip

    with gzip.open(tmp_path / "kjv.txt.gz", "wt", encoding="utf-8") as lines:
        lines.write("GEN 1:1\tA test verse.\n")
    scripture = BundledScripture(tmp_path)
    assert scripture.text("kjv", (VerseRef("GEN", 1, 1),)) == "A test verse."
    assert (
        scripture.text("kjv", (VerseRef("GEN", 1, 1),)) == "A test verse."
    )  # cached on the second read
