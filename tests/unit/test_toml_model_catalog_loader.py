"""Loading a model catalog from TOML: the happy path, the documented example, and every refusal."""

import re
from datetime import date
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.models.toml_model_catalog_loader import (
    TomlModelCatalogLoader,
)
from engineering_influence.interfaces.model_catalog_loader_interface import (
    ModelCatalogLoaderInterface,
)

DOCS = Path(__file__).parent.parent.parent / "docs" / "MODEL_CATALOG.md"

HEADER = """
[[model]]
provider = "acme"
model = "acme-1"
family = "acme"
context_window = 1000
max_output_tokens = 100
usage_policy_url = "https://example.test/policy"
"""
PRICE = """
[[model.price]]
effective = "2026-01-01"
input = 1000000
output = 5000000
cache_read = 100000
cache_write = 1250000
batch_discount_percent = 50
"""


def load(tmp_path: Path, text: str):  # type: ignore[no-untyped-def]
    path = tmp_path / "catalog.toml"
    path.write_text(text, encoding="utf-8")
    return TomlModelCatalogLoader().load(path)


def refusal(tmp_path: Path, text: str) -> ApplicationError:
    with pytest.raises(ApplicationError) as caught:
        load(tmp_path, text)
    assert caught.value.code == "MODEL_CATALOG_INVALID"
    return caught.value


def test_it_is_a_loader() -> None:
    assert isinstance(TomlModelCatalogLoader(), ModelCatalogLoaderInterface)


def test_a_catalog_expands_each_price_into_a_descriptor(tmp_path: Path) -> None:
    second = PRICE.replace("2026-01-01", "2026-07-01").replace("1000000", "2000000", 1)
    catalog = load(tmp_path, HEADER + PRICE + second)
    early = catalog.descriptor("acme", "acme-1", date(2026, 2, 1))
    late = catalog.descriptor("acme", "acme-1", date(2026, 8, 1))
    assert (early.input_micro_usd_per_mtok, late.input_micro_usd_per_mtok) == (1_000_000, 2_000_000)
    assert (early.family, early.context_window, early.max_output_tokens) == ("acme", 1000, 100)
    assert early.cache_write_micro_usd_per_mtok == 1_250_000
    assert early.long_context_threshold_tokens == 0
    assert early.long_context_input_percent == 100


def test_long_context_keys_are_read_when_present(tmp_path: Path) -> None:
    extra = (
        "long_context_threshold_tokens = 200000\n"
        "long_context_input_percent = 200\nlong_context_output_percent = 150\n"
    )
    catalog = load(tmp_path, HEADER + PRICE + extra)
    d = catalog.descriptor("acme", "acme-1", date(2026, 2, 1))
    assert (d.long_context_threshold_tokens, d.long_context_input_percent) == (200_000, 200)
    assert d.long_context_output_percent == 150


def test_the_documented_example_loads_and_prices_a_call(tmp_path: Path) -> None:
    block = re.search(r"```toml\n(.*?)```", DOCS.read_text(encoding="utf-8"), re.DOTALL)
    assert block is not None
    catalog = load(tmp_path, block.group(1))
    early = catalog.descriptor("example", "example-model", date(2026, 3, 1))
    late = catalog.descriptor("example", "example-model", date(2026, 9, 1))
    assert early.input_micro_usd_per_mtok == 3_000_000
    assert late.long_context_input_percent == 200


def test_an_empty_file_is_an_empty_catalog(tmp_path: Path) -> None:
    with pytest.raises(ApplicationError) as caught:
        load(tmp_path, "").descriptor("acme", "acme-1", date(2026, 1, 1))
    assert caught.value.code == "MODEL_UNPRICED"


def test_a_model_without_a_price_is_refused_by_name(tmp_path: Path) -> None:
    assert (
        "model #1 (acme/acme-1) has no [[model.price]] entry" in refusal(tmp_path, HEADER).message
    )


def test_a_missing_key_names_the_entry_and_the_key(tmp_path: Path) -> None:
    message = refusal(tmp_path, HEADER.replace('family = "acme"\n', "") + PRICE).message
    assert "model #1 (acme/acme-1) is missing 'family'" in message
    message = refusal(tmp_path, HEADER + PRICE.replace("cache_read = 100000\n", "")).message
    assert "missing 'cache_read'" in message


def test_a_value_the_descriptor_rejects_names_the_entry(tmp_path: Path) -> None:
    message = refusal(tmp_path, HEADER + PRICE.replace("2026-01-01", "soon")).message
    assert message.startswith("model #1 (acme/acme-1): ")
    assert "ISO date" in message


def test_a_wrong_type_is_refused_not_crashed_on(tmp_path: Path) -> None:
    message = refusal(
        tmp_path, HEADER.replace("context_window = 1000", 'context_window = "big"') + PRICE
    ).message
    assert message.startswith("model #1 (acme/acme-1): ")


def test_two_prices_with_one_date_are_refused(tmp_path: Path) -> None:
    assert "same effective date" in refusal(tmp_path, HEADER + PRICE + PRICE).message


def test_a_second_model_is_numbered_in_the_message(tmp_path: Path) -> None:
    second = HEADER.replace("acme-1", "acme-2").replace('family = "acme"\n', "") + PRICE
    assert (
        "model #2 (acme/acme-2) is missing 'family'"
        in refusal(tmp_path, HEADER + PRICE + second).message
    )


def test_invalid_toml_and_a_missing_file_are_refused(tmp_path: Path) -> None:
    assert "is not valid TOML" in refusal(tmp_path, "[[model").message
    with pytest.raises(ApplicationError, match="cannot read"):
        TomlModelCatalogLoader().load(tmp_path / "absent.toml")
