# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The Living Waters fountains, read with the Fountain parser and format check, when the author's folder is present.

The scripts are the author's and are never copied here. Point `EI_LIVING_WATERS_DIR` at the folder that holds the
`film-*/` directories; without it every test in this file is skipped. The assertions pin what the parser must always
do (find every scene heading) and what the checker must always do (run on a real script and return its findings).
They do not pin how many problems the scripts have, because those are the author's to fix.
"""

import os
import re
from pathlib import Path

import pytest

from engineering_influence.services.fountain_format_check import FountainFormatCheck
from engineering_influence.services.fountain_parser import FountainParser

ROOT = os.environ.get("EI_LIVING_WATERS_DIR")
FOUNTAINS = (
    tuple(sorted(Path(ROOT).glob("film-*/*.fountain"))) if ROOT and Path(ROOT).is_dir() else ()
)

pytestmark = pytest.mark.skipif(
    not FOUNTAINS, reason="EI_LIVING_WATERS_DIR is not set or holds no film-*/*.fountain files"
)

HEADING = re.compile(r"^(?:INT|EXT|INT\./EXT|I/E)[ .]", re.MULTILINE)


@pytest.mark.parametrize("path", FOUNTAINS, ids=lambda path: path.name)
def test_the_parser_finds_every_scene_heading_in_the_script(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    scenes = FountainParser().scenes(text)

    assert len(scenes) == len(HEADING.findall(text))


@pytest.mark.parametrize("path", FOUNTAINS, ids=lambda path: path.name)
def test_the_script_opens_with_a_living_waters_title_page(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    title = dict(FountainParser().title_page(text)).get("Title", "")

    assert title.startswith("LIVING WATERS")


@pytest.mark.parametrize("path", FOUNTAINS, ids=lambda path: path.name)
def test_the_format_check_runs_on_the_script_and_returns_its_findings(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    checker = FountainFormatCheck(FountainParser())

    problems = checker.problems(text)
    notes = checker.notes(text)

    assert all(isinstance(problem, str) for problem in problems)
    assert all(isinstance(note, str) for note in notes)
