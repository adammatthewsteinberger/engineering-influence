# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""RevisionPass: what one editing pass reads, writes, is told and may change."""

from typing import Any

import pytest

from engineering_influence.models.interfaces.revision_pass_interface import (
    RevisionPassInterface,
)
from engineering_influence.models.revision_pass import RevisionPass


def make(**changes: Any) -> RevisionPass:
    fields: dict[str, Any] = {
        "stage": "revise_lines",
        "template": "stage_revise_lines",
        "source": "structure",
        "output": "lines",
        "blanks": ("voice", "chapter"),
        "min_ratio": 0.9,
        "max_ratio": 1.1,
    }
    return RevisionPass(**{**fields, **changes})


def refused(**changes: Any) -> str:
    with pytest.raises((ValueError, TypeError)) as error:
        make(**changes)
    return str(error.value)


def test_a_pass_names_its_stage_template_files_blanks_and_length_bounds() -> None:
    made = make()
    assert isinstance(made, RevisionPassInterface)
    assert (made.stage, made.template, made.source, made.output) == (
        "revise_lines",
        "stage_revise_lines",
        "structure",
        "lines",
    )
    assert made.blanks == ("voice", "chapter") and (made.min_ratio, made.max_ratio) == (0.9, 1.1)


@pytest.mark.parametrize("field", ["stage", "template", "source", "output"])
def test_names_are_lowercase_words(field: str) -> None:
    for bad in ("", "Upper", "1st", "has space", "dash-ed", 3):
        assert "lowercase letters, digits and underscores" in refused(**{field: bad})


def test_a_pass_writes_different_files_from_the_ones_it_reads() -> None:
    assert (
        refused(source="same", output="same")
        == "a pass writes different files from the ones it reads"
    )


def test_a_pass_is_always_told_the_chapter_and_only_known_things_once() -> None:
    assert refused(blanks=("voice",)) == "a pass is told the chapter it revises"
    assert refused(blanks=["chapter"]) == "a pass is told the chapter it revises"
    assert "each once" in refused(blanks=("chapter", "chapter"))
    assert "each once" in refused(blanks=("chapter", "secrets"))
    assert make(blanks=("outline", "summaries", "beats", "voice", "chapter"))


@pytest.mark.parametrize(
    ("low", "high"), [(1.0, 1.1), (0.0, 1.1), (-0.5, 1.1), (0.9, 1.0), (1.1, 0.9), (1.2, 1.3)]
)
def test_the_ratios_straddle_one(low: float, high: float) -> None:
    assert "straddle 1" in refused(min_ratio=low, max_ratio=high)
