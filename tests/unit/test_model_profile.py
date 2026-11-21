# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A profile names how to reach a model, and refuses what would leak or silently misconfigure."""

import pytest

from engineering_influence.models.model_profile import ModelProfile

KEY_LIKE = "sk-ant-api03-SECRETSECRETSECRET"


def profile(**changes: str) -> ModelProfile:
    fields = {
        "name": "p",
        "adapter": "openai_compatible",
        "provider": "local",
        "model": "m",
        "base_url": "http://127.0.0.1:11434",
    }
    fields.update(changes)
    return ModelProfile(**fields)


def test_a_local_profile_needs_no_key() -> None:
    local = profile()
    assert local.requires_key() is False
    assert local.sends_key_in_clear() is False


@pytest.mark.parametrize(
    "changes",
    [
        {"name": " "},
        {"provider": ""},
        {"model": "  "},
        {"adapter": "carrier-pigeon"},
        {"output_cap_field": "limit"},
        {"base_url": "ftp://host"},
        {"base_url": "http://"},
        {"base_url": "not a url"},
        {"base_url": "https://user:pw@host"},
        {"base_url": "https://user@host"},
        {"adapter": "anthropic", "base_url": "https://api.anthropic.com"},
    ],
)
def test_a_profile_that_cannot_work_is_refused(changes: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        profile(**changes)


@pytest.mark.parametrize("value", [KEY_LIKE, "lower_case", "HAS-DASH", "1LEADING", "WITH SPACE"])
def test_a_key_pasted_where_a_variable_name_belongs_is_refused_without_being_repeated(
    value: str,
) -> None:
    with pytest.raises(ValueError) as caught:
        profile(api_key_env=value)
    assert value not in str(caught.value)
    assert "NAME of an environment variable" in str(caught.value)


@pytest.mark.parametrize("name", ["ANTHROPIC_API_KEY", "_X", "KEY_2"])
def test_a_variable_name_is_accepted_and_makes_the_key_required(name: str) -> None:
    assert profile(api_key_env=name).requires_key() is True


@pytest.mark.parametrize("field", ["max_tokens", "max_completion_tokens"])
def test_both_output_cap_fields_are_accepted(field: str) -> None:
    assert profile(output_cap_field=field).output_cap_field == field


@pytest.mark.parametrize(
    ("base_url", "key", "clear"),
    [
        ("https://api.example.com", "K", False),
        ("http://api.example.com", "K", True),
        ("http://10.0.0.5:8000", "K", True),
        ("http://localhost:11434", "K", False),
        ("http://127.0.0.1:11434", "K", False),
        ("http://[::1]:11434", "K", False),
        ("http://api.example.com", "", False),
    ],
)
def test_only_a_key_over_plain_http_to_another_host_is_sent_in_clear(
    base_url: str, key: str, clear: bool
) -> None:
    assert profile(base_url=base_url, api_key_env=key).sends_key_in_clear() is clear
