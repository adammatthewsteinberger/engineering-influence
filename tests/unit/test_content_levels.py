"""Violence and heat levels: on the brief, on the stored run, as a model's recorded ceiling, and the check between them."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from engineering_influence.contracts.brief.v1.book_brief_v1 import BookBriefV1
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.models.toml_model_catalog_loader import (
    TomlModelCatalogLoader,
)
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.repositories.book_run_codec import BookRunCodec
from engineering_influence.services.content_policy import ContentPolicy

VIOLENCE = ("none", "mild", "moderate", "graphic")
HEAT = ("none", "sweet", "steamy", "explicit")


def novel(**changes: Any) -> BookBrief:
    return BookBrief(BookKind.NOVEL, "a heist", 1_000_000, **changes)


def model(**changes: Any) -> ProviderDescriptor:
    values: dict[str, Any] = {
        "provider": "acme",
        "model": "acme-1",
        "family": "acme",
        "context_window": 1000,
        "max_output_tokens": 100,
        "input_micro_usd_per_mtok": 1,
        "output_micro_usd_per_mtok": 1,
        "cache_read_micro_usd_per_mtok": 1,
        "cache_write_micro_usd_per_mtok": 1,
        "batch_discount_percent": 0,
        "price_effective": "2026-01-01",
        "usage_policy_url": "https://example.test/policy",
    }
    values.update(changes)
    return ProviderDescriptor(**values)


def test_the_levels_are_ordered_mildest_first() -> None:
    assert BookBrief.VIOLENCE_LEVELS == VIOLENCE
    assert BookBrief.HEAT_LEVELS == HEAT


def test_a_brief_sets_no_level_by_default() -> None:
    value = novel()
    assert (value.violence, value.heat) == (None, None)
    assert BookBrief(BookKind.NONFICTION, "x", 1).violence is None


@pytest.mark.parametrize("level", VIOLENCE)
def test_each_violence_level_is_accepted_for_a_novel(level: str) -> None:
    assert novel(violence=level).violence == level


@pytest.mark.parametrize("level", HEAT)
def test_each_heat_level_is_accepted_for_a_novel(level: str) -> None:
    assert novel(heat=level).heat == level


def test_a_level_outside_the_list_is_refused_and_named() -> None:
    with pytest.raises(ValueError, match="violence must be one of none, mild, moderate, graphic"):
        novel(violence="brutal")
    with pytest.raises(ValueError, match="heat must be one of none, sweet, steamy, explicit"):
        novel(heat="Steamy")


@pytest.mark.parametrize("field", ["violence", "heat"])
def test_only_a_novel_may_set_a_level(field: str) -> None:
    with pytest.raises(ValueError, match="apply to a novel"):
        BookBrief(BookKind.NONFICTION, "x", 1, **{field: "none"})


def brief_document(**changes: Any) -> dict[str, Any]:
    return {"kind": "novel", "idea": "a heist", "budget_micro_usd": 5_000_000, **changes}


def test_the_contract_reads_levels_and_defaults_to_none() -> None:
    plain = BookBriefV1.model_validate(brief_document())
    assert (plain.violence, plain.heat) == (None, None)
    value = BookBriefV1.model_validate(brief_document(violence="moderate", heat="sweet"))
    model_value = value.to_model()
    assert (model_value.violence, model_value.heat) == ("moderate", "sweet")


@pytest.mark.parametrize("level", VIOLENCE)
def test_the_contract_accepts_each_violence_level(level: str) -> None:
    assert BookBriefV1.model_validate(brief_document(violence=level)).to_model().violence == level


@pytest.mark.parametrize("level", HEAT)
def test_the_contract_accepts_each_heat_level(level: str) -> None:
    assert BookBriefV1.model_validate(brief_document(heat=level)).to_model().heat == level


@pytest.mark.parametrize("changes", [{"violence": "brutal"}, {"heat": "mild"}, {"violence": 3}])
def test_the_contract_refuses_a_level_outside_the_list(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        BookBriefV1.model_validate(brief_document(**changes))


def test_the_contract_refuses_a_level_on_nonfiction() -> None:
    with pytest.raises(ValidationError, match="apply to a novel"):
        BookBriefV1.model_validate(brief_document(kind="nonfiction", violence="none"))


def stored(brief: BookBrief) -> BookRun:
    return BookRun("run-1", brief, StagePlan(brief.kind, ("brief", "outline")), Budget(1_000_000))


def test_levels_round_trip_through_a_stored_run() -> None:
    codec = BookRunCodec()
    made = stored(novel(violence="graphic", heat="none"))
    assert codec.decode(codec.encode(made)) == made


def test_a_run_stored_before_levels_existed_loads_with_none() -> None:
    codec = BookRunCodec()
    document = json.loads(codec.encode(stored(novel())))
    del document["brief"]["violence"], document["brief"]["heat"]
    loaded = codec.decode(json.dumps(document)).brief
    assert (loaded.violence, loaded.heat) == (None, None)


def test_a_model_records_no_ceiling_by_default() -> None:
    value = model()
    assert (value.max_violence, value.max_heat) == (None, None)


@pytest.mark.parametrize(("field", "levels"), [("max_violence", VIOLENCE), ("max_heat", HEAT)])
def test_a_ceiling_is_one_of_the_levels(field: str, levels: tuple[str, ...]) -> None:
    for level in levels:
        assert getattr(model(**{field: level}), field) == level
    with pytest.raises(ValueError, match=f"{field} must be one of {', '.join(levels)}"):
        model(**{field: "everything"})


ENTRY = """
[[model]]
provider = "acme"
model = "acme-1"
family = "acme"
context_window = 1000
max_output_tokens = 100
usage_policy_url = "https://example.test/policy"
{extra}
[[model.price]]
effective = "2026-01-01"
input = 1
output = 1
cache_read = 1
cache_write = 1
batch_discount_percent = 0
"""


def load(tmp_path: Path, extra: str):  # type: ignore[no-untyped-def]
    path = tmp_path / "catalog.toml"
    path.write_text(ENTRY.format(extra=extra), encoding="utf-8")
    return TomlModelCatalogLoader().load(path).descriptor("acme", "acme-1", date(2026, 2, 1))


def test_a_catalog_entry_may_record_ceilings(tmp_path: Path) -> None:
    value = load(tmp_path, 'max_violence = "moderate"\nmax_heat = "steamy"')
    assert (value.max_violence, value.max_heat) == ("moderate", "steamy")


def test_a_catalog_entry_records_nothing_unless_it_says_so(tmp_path: Path) -> None:
    value = load(tmp_path, "")
    assert (value.max_violence, value.max_heat) == (None, None)


def test_a_catalog_entry_with_an_unknown_ceiling_is_refused_by_name(tmp_path: Path) -> None:
    with pytest.raises(ApplicationError) as caught:
        load(tmp_path, 'max_heat = "wild"')
    assert caught.value.code == "MODEL_CATALOG_INVALID"
    assert "model #1 (acme/acme-1): max_heat must be one of" in caught.value.message


POLICY = ContentPolicy()


def test_a_brief_that_sets_no_level_is_never_refused() -> None:
    assert POLICY.problems(novel(), model()) == ()
    POLICY.require(novel(), model())


@pytest.mark.parametrize(("violence", "heat"), [("none", "none"), ("mild", "sweet")])
def test_the_baseline_is_allowed_when_nothing_is_recorded(violence: str, heat: str) -> None:
    assert POLICY.problems(novel(violence=violence, heat=heat), model()) == ()


def test_more_than_the_baseline_is_refused_when_nothing_is_recorded() -> None:
    (violence,) = POLICY.problems(novel(violence="moderate"), model())
    assert violence == (
        "the brief asks for violence moderate, and no violence ceiling is recorded for acme/acme-1, "
        "so mild is the most it may ask; read https://example.test/policy and set max_violence in "
        "the catalog entry"
    )
    (heat,) = POLICY.problems(novel(heat="steamy"), model())
    assert heat == (
        "the brief asks for heat steamy, and no heat ceiling is recorded for acme/acme-1, "
        "so sweet is the most it may ask; read https://example.test/policy and set max_heat in "
        "the catalog entry"
    )


@pytest.mark.parametrize(("wanted", "ok"), [("mild", True), ("moderate", True), ("graphic", False)])
def test_a_recorded_ceiling_is_the_most_allowed(wanted: str, ok: bool) -> None:
    found = POLICY.problems(novel(violence=wanted), model(max_violence="moderate"))
    assert (found == ()) is ok
    if not ok:
        assert found == (
            "the brief asks for violence graphic, but acme/acme-1 is recorded as allowing up to moderate",
        )


def test_a_recorded_ceiling_may_be_lower_than_the_baseline() -> None:
    (found,) = POLICY.problems(novel(heat="sweet"), model(max_heat="none"))
    assert found.endswith("is recorded as allowing up to none")


def test_a_recorded_ceiling_may_be_above_the_baseline() -> None:
    assert (
        POLICY.problems(
            novel(violence="graphic", heat="explicit"),
            model(max_violence="graphic", max_heat="explicit"),
        )
        == ()
    )


def test_each_level_is_judged_on_its_own_ceiling() -> None:
    found = POLICY.problems(
        novel(violence="graphic", heat="explicit"), model(max_violence="graphic", max_heat="sweet")
    )
    assert len(found) == 1 and found[0].startswith("the brief asks for heat explicit")


def test_both_refusals_are_reported_together() -> None:
    found = POLICY.problems(novel(violence="graphic", heat="explicit"), model())
    assert [item.split(",")[0] for item in found] == [
        "the brief asks for violence graphic",
        "the brief asks for heat explicit",
    ]


def test_require_passes_when_allowed() -> None:
    POLICY.require(novel(violence="mild"), model())


def test_require_refuses_with_a_code_and_every_reason() -> None:
    with pytest.raises(ApplicationError) as caught:
        POLICY.require(novel(violence="graphic", heat="explicit"), model())
    error = caught.value
    assert (error.code, error.http_status) == ("CONTENT_LEVEL_NOT_ALLOWED", 422)
    assert (
        "violence graphic" in error.message
        and "; the brief asks for heat explicit" in error.message
    )
