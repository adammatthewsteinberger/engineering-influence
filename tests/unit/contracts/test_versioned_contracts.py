"""The versioned contracts: the brief, the book config and the broker message."""

import tomllib
from pathlib import Path
from typing import Any, Literal, get_args, get_origin

import pytest
from pydantic import ValidationError

from engineering_influence.contracts.book_config.v1.book_config_entry_v1 import BookConfigEntryV1
from engineering_influence.contracts.book_config.v1.book_config_v1 import BookConfigV1
from engineering_influence.contracts.brief.v1.book_brief_v1 import BookBriefV1
from engineering_influence.contracts.job_message import JobMessage
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.typesetting.paper_stock import PaperStock
from engineering_influence.models.typesetting.trim_size import TrimSize
from engineering_influence.services.publishing.config_entries import ConfigEntries

FIXTURE = Path(__file__).parents[2] / "fixtures/fixture_book/books/fixture.toml"


def brief(**changes: Any) -> dict[str, Any]:
    return {
        "kind": "nonfiction",
        "idea": "a field guide to sourdough",
        "budget_micro_usd": 5_000_000,
        **changes,
    }


def test_a_minimal_brief_is_version_1_with_defaults() -> None:
    value = BookBriefV1.model_validate(brief())
    assert (value.schema_version, value.kind, value.language) == (1, BookKind.NONFICTION, "en")
    assert (value.title_hint, value.audience, value.target_words, value.trim_size) == (None,) * 4


def test_a_brief_is_read_from_json_and_trimmed() -> None:
    value = BookBriefV1.model_validate_json(
        '{"kind": "novel", "idea": "  a heist  ", "budget_micro_usd": 1, "target_words": 60000}'
    )
    assert (value.kind, value.idea, value.target_words) == (BookKind.NOVEL, "a heist", 60_000)


@pytest.mark.parametrize(
    "changes",
    [
        {"idea": "  "},
        {"idea": None},
        {"kind": "screenplay"},
        {"budget_micro_usd": 0},
        {"budget_micro_usd": 2.5},
        {"target_words": 0},
        {"language": ""},
        {"title_hint": " "},
        {"schema_version": 2},
        {"voice": "dry"},
    ],
)
def test_a_brief_refuses_what_cannot_start_a_run(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        BookBriefV1.model_validate(brief(**changes))


def test_a_brief_requires_a_budget() -> None:
    document = brief()
    del document["budget_micro_usd"]
    with pytest.raises(ValidationError, match="budget_micro_usd"):
        BookBriefV1.model_validate(document)


def test_a_brief_becomes_the_model_a_run_is_built_from() -> None:
    value = BookBriefV1.model_validate(
        brief(
            title_hint="Rise",
            audience="home bakers",
            target_words=50_000,
            trim_size="5x8",
            language="fr",
        )
    )
    model = value.to_model()
    assert (model.kind, model.idea, model.budget_micro_usd) == (
        BookKind.NONFICTION,
        value.idea,
        5_000_000,
    )
    assert (model.title_hint, model.audience, model.target_words) == ("Rise", "home bakers", 50_000)
    assert (model.trim_size, model.language) == ("5x8", "fr")


def test_a_brief_cannot_be_changed_after_it_is_read() -> None:
    with pytest.raises(ValidationError, match="frozen"):
        BookBriefV1.model_validate(brief()).idea = "other"  # type: ignore[misc]


def test_the_fixture_book_config_is_a_valid_config() -> None:
    config = BookConfigV1.model_validate(tomllib.loads(FIXTURE.read_text(encoding="utf-8")))
    assert config.source == "src"
    assert [entry.file for entry in config.front] == ["00-foreword.md"]
    assert [part.title for part in config.parts] == ["Part One: Light", "Part Two: Dark"]
    assert config.not_in_book == ()


def test_everything_else_in_a_config_travels_as_metadata() -> None:
    config = BookConfigV1.model_validate(tomllib.loads(FIXTURE.read_text(encoding="utf-8")))
    assert config.model_extra is not None
    assert config.model_extra["title"] == "The Lighthouse Ledger"
    assert config.model_extra["release"]["required"] is True


def test_the_contract_orders_a_book_exactly_as_the_publisher_does() -> None:
    raw = tomllib.loads(FIXTURE.read_text(encoding="utf-8"))
    config = BookConfigV1.model_validate(raw)
    ordered: list[tuple[str, str, str, int | None]] = [
        ("front", e.file, e.style, None) for e in config.front
    ]
    number = 0
    for part in config.parts:
        for chapter in part.chapters:
            number += 1
            ordered.append(("chapter", chapter.file, chapter.style, number))
    ordered += [("back", e.file, e.style, None) for e in config.back]
    assert ordered == ConfigEntries().iterate(raw)


def test_an_entry_is_a_bare_name_or_a_table() -> None:
    bare = BookConfigEntryV1.model_validate("a.md")
    table = BookConfigEntryV1.model_validate(
        {"file": "refs.md", "style": "references", "short": "Refs"}
    )
    assert (bare.file, bare.style, bare.short) == ("a.md", "prose", None)
    assert (table.file, table.style, table.short) == ("refs.md", "references", "Refs")


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"source": " "},
        {"source": "src", "front": [""]},
        {"source": "src", "front": [{"style": "prose"}]},
        {"source": "src", "parts": [{"chapters": ["a.md"]}]},
        {"source": "src", "parts": [{"title": "One"}]},
        {"source": "src", "not_in_book": [""]},
    ],
)
def test_a_config_refuses_what_the_loader_cannot_read(document: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        BookConfigV1.model_validate(document)


def message(**changes: Any) -> bytes:
    import json

    document = {"job_id": "job-1", "kind": "pipeline.thesis", "payload": {"project_slug": "demo"}}
    return json.dumps({**document, **changes}).encode()


def test_a_message_without_a_version_is_read_as_version_1() -> None:
    assert JobMessage.parse(message()).schema_version == 1


def test_a_message_states_its_version_and_keeps_it() -> None:
    parsed = JobMessage.parse(message(schema_version=1))
    assert parsed.model_dump()["schema_version"] == 1


@pytest.mark.parametrize("version", [0, 2, "1"])
def test_a_message_of_another_version_is_refused(version: object) -> None:
    with pytest.raises(ValidationError):
        JobMessage.parse(message(schema_version=version))


def test_a_book_config_is_nonfiction_unless_it_says_it_is_a_novel() -> None:
    assert BookConfigV1.model_validate({"source": "src"}).kind is BookKind.NONFICTION
    assert BookConfigV1.model_validate({"source": "src", "kind": "novel"}).kind is BookKind.NOVEL


def test_a_book_config_with_an_unknown_kind_is_refused() -> None:
    with pytest.raises(ValidationError):
        BookConfigV1.model_validate({"source": "src", "kind": "poem"})


def test_the_kind_is_a_field_of_the_config_and_not_left_among_the_extras() -> None:
    config = BookConfigV1.model_validate({"source": "src", "kind": "novel", "title": "T"})
    assert config.model_extra == {"title": "T"}


def test_a_book_config_defaults_to_six_by_nine_on_white_paper() -> None:
    config = BookConfigV1.model_validate({"source": "src"})
    assert (config.trim_size, config.paper) == ("6x9", "white")


def test_a_book_config_takes_every_trim_size_and_paper_the_models_know() -> None:
    for trim in TrimSize.names():
        for paper in PaperStock.names():
            config = BookConfigV1.model_validate(
                {"source": "src", "trim_size": trim, "paper": paper}
            )
            assert (config.trim_size, config.paper) == (trim, paper)


def test_the_contracts_name_exactly_the_trim_sizes_and_papers_the_models_have() -> None:
    assert get_args(BookConfigV1.model_fields["trim_size"].annotation) == TrimSize.names()
    assert get_args(BookConfigV1.model_fields["paper"].annotation) == PaperStock.names()
    optional = get_args(BookBriefV1.model_fields["trim_size"].annotation)
    literal = next(part for part in optional if get_origin(part) is Literal)
    assert get_args(literal) == TrimSize.names()


@pytest.mark.parametrize(
    "extra", [{"trim_size": "A5"}, {"paper": "glossy"}, {"trim_size": ""}, {"paper": "Cream"}]
)
def test_a_book_config_with_an_unknown_trim_size_or_paper_is_refused(extra: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        BookConfigV1.model_validate({"source": "src", **extra})


def test_a_brief_takes_a_known_trim_size_and_refuses_an_unknown_one() -> None:
    assert BookBriefV1.model_validate(brief(trim_size="5x8")).to_model().trim_size == "5x8"
    with pytest.raises(ValidationError):
        BookBriefV1.model_validate(brief(trim_size="7x10"))


def test_a_book_config_with_no_schema_version_is_version_one_and_another_version_is_refused() -> (
    None
):
    from pydantic import ValidationError

    from engineering_influence.contracts.book_config.v1.book_config_v1 import BookConfigV1

    assert BookConfigV1.model_validate({"source": "src"}).schema_version == 1
    assert BookConfigV1.model_validate({"source": "src", "schema_version": 1}).schema_version == 1
    with pytest.raises(ValidationError):
        BookConfigV1.model_validate({"source": "src", "schema_version": 2})
