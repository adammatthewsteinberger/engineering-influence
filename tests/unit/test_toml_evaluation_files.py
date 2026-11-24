"""The rubric, the set and the baseline are read strictly, and the shipped ones load."""

import json
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.evaluation.toml_evaluation_files import (
    TomlEvaluationFiles,
)
from engineering_influence.interfaces.evaluation_files_interface import EvaluationFilesInterface
from engineering_influence.models.book_kind import BookKind

REPO = Path(__file__).resolve().parents[2]
RUBRIC = """
version = 2
pass_mean = 3.5
max_drop = 0.2

[[dimension]]
name = "voice"
question = "Is it its own?"
kinds = ["nonfiction", "novel"]
[dimension.anchors]
1 = "generic"
3 = "uneven"
5 = "distinct"

[[dimension]]
name = "plot"
question = "Does it move?"
kinds = ["novel"]
[dimension.anchors]
1 = "stalls"
3 = "moves"
5 = "drives"
"""
CASES = """
[[case]]
name = "herbs"
kind = "nonfiction"
idea = "Herbs indoors"
title_hint = "Herbs"
target_words = 10000

[[case]]
name = "lamp"
kind = "novel"
idea = "A lamp"
trim_size = "5.5x8.5"
"""


def files() -> TomlEvaluationFiles:
    return TomlEvaluationFiles()


def write(tmp_path: Path, text: str, name: str = "f.toml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def refused(call, path: Path) -> str:  # type: ignore[no-untyped-def]
    with pytest.raises(ApplicationError) as error:
        call(path)
    assert error.value.code == "EVALUATION_FILE_INVALID" and error.value.http_status == 422
    assert str(path) in error.value.message
    return str(error.value.message)


def test_the_rubric_is_read_with_its_dimensions_anchors_and_bar(tmp_path: Path) -> None:
    rubric = files().rubric(write(tmp_path, RUBRIC))
    assert isinstance(files(), EvaluationFilesInterface)
    assert (rubric.version, rubric.pass_mean, rubric.max_drop) == (2, 3.5, 0.2)
    voice, plot = rubric.dimensions
    assert (voice.name, voice.kinds, voice.anchors[1]) == (
        "voice",
        ("nonfiction", "novel"),
        (3, "uneven"),
    )
    assert plot.kinds == ("novel",)


def test_the_cases_are_read_in_order_with_their_options(tmp_path: Path) -> None:
    herbs, lamp = files().cases(write(tmp_path, CASES))
    assert (herbs.name, herbs.kind, herbs.title_hint, herbs.target_words) == (
        "herbs",
        BookKind.NONFICTION,
        "Herbs",
        10000,
    )
    assert (lamp.kind, lamp.trim_size, lamp.title_hint) == (BookKind.NOVEL, "5.5x8.5", None)


def test_the_shipped_rubric_and_set_load_and_cover_both_kinds() -> None:
    rubric = files().rubric(REPO / "evaluation" / "rubric.toml")
    cases = files().cases(REPO / "evaluation" / "set.toml")
    assert (rubric.pass_mean, rubric.max_drop) == (3.5, 0.2)
    assert {case.kind for case in cases} == {BookKind.NONFICTION, BookKind.NOVEL}
    assert len(cases) >= 4 and len(rubric.dimensions) >= 6


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("this is = not toml [", "not valid TOML"),
        (RUBRIC + "\nextra = 1", "unknown keys ['extra']"),
        ("version = 1", "at least one [[dimension]]"),
        (
            RUBRIC.replace('question = "Is it its own?"', 'question = "q"\nbogus = 1'),
            "unknown keys",
        ),
        (RUBRIC.replace('5 = "distinct"', '4 = "x"'), "unknown keys ['4']"),
        (
            RUBRIC.replace(
                '[dimension.anchors]\n1 = "generic"\n3 = "uneven"\n5 = "distinct"\n', ""
            ),
            "a table was expected",
        ),
        (RUBRIC.replace('name = "voice"', 'name = "Voice"'), "lowercase"),
        (RUBRIC.replace("pass_mean = 3.5", "pass_mean = 9"), "pass mark"),
        (RUBRIC.replace("version = 2", 'version = "two"'), "version"),
        (RUBRIC.replace("max_drop = 0.2\n", ""), "allowed drop"),
        (RUBRIC.replace('kinds = ["novel"]', 'kinds = "novel"'), "dimension plot"),
        (RUBRIC.replace('kinds = ["novel"]', "kinds = [1]"), "dimension plot"),
    ],
)
def test_a_rubric_that_is_not_usable_is_refused_with_the_file_named(
    tmp_path: Path, text: str, why: str
) -> None:
    assert why in refused(files().rubric, write(tmp_path, text))


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("x = [", "not valid TOML"),
        ("a = 1", "unknown keys"),
        ("", "at least one [[case]]"),
        (CASES.replace('kind = "novel"', 'kind = "poem"'), "lamp"),
        (CASES.replace('idea = "A lamp"', 'idea = ""'), "lamp"),
        (CASES.replace('name = "lamp"', 'name = "Lamp"'), "lowercase"),
        (CASES.replace('name = "lamp"', 'name = "herbs"'), "each case is named once"),
        (
            CASES.replace('title_hint = "Herbs"', 'title_hint = "H"\nmood = 1'),
            "unknown keys ['mood']",
        ),
        (CASES.replace("target_words = 10000", "target_words = 5.5"), "herbs"),
        ('[[case]]\nname = "x"', "x:"),
        ("case = [1]", "a table was expected"),
    ],
)
def test_a_set_that_is_not_usable_is_refused(tmp_path: Path, text: str, why: str) -> None:
    assert why in refused(files().cases, write(tmp_path, text))


def test_a_file_that_is_missing_unreadable_or_too_big_is_refused(tmp_path: Path) -> None:
    assert "cannot be read (FileNotFoundError)" in refused(files().cases, tmp_path / "nope.toml")
    binary = tmp_path / "b.toml"
    binary.write_bytes(b"\xff\xfe\x00")
    assert "cannot be read (UnicodeDecodeError)" in refused(files().cases, binary)
    big = write(tmp_path, "#" * TomlEvaluationFiles.MAX_BYTES + "\n", "big.toml")
    assert f"larger than {TomlEvaluationFiles.MAX_BYTES} bytes" in refused(files().cases, big)
    exact = write(
        tmp_path, CASES + "#" * (TomlEvaluationFiles.MAX_BYTES - len(CASES.encode())), "exact.toml"
    )
    assert exact.stat().st_size == TomlEvaluationFiles.MAX_BYTES
    assert len(files().cases(exact)) == 2


def test_a_baseline_is_the_dimension_means_of_an_earlier_report(tmp_path: Path) -> None:
    path = write(
        tmp_path, json.dumps({"dimension_means": {"voice": 4, "plot": 3.5}, "x": 1}), "b.json"
    )
    assert files().baseline(path) == {"voice": 4.0, "plot": 3.5}


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("{not", "not valid JSON"),
        ("[1]", "no dimension_means"),
        ("{}", "no dimension_means"),
        ('{"dimension_means": {}}', "no dimension_means"),
        ('{"dimension_means": [1]}', "no dimension_means"),
        ('{"dimension_means": {"voice": "4"}}', "is a number"),
        ('{"dimension_means": {"voice": true}}', "is a number"),
    ],
)
def test_a_baseline_that_is_not_an_evaluation_report_is_refused(
    tmp_path: Path, text: str, why: str
) -> None:
    assert why in refused(files().baseline, write(tmp_path, text, "b.json"))
