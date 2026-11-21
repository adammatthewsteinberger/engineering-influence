# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""CassetteRedactor: it masks named secrets and key-shaped text, and leaves prose alone."""

import pytest

from engineering_influence.infrastructure.cassettes.cassette_redactor import CassetteRedactor

KEY = "sk-test-SECRETSECRET"
MASK = "[REDACTED]"
UNNAMED = "sk-ant-" + "A1b2" * 6


def test_a_named_secret_is_masked_wherever_it_sits_in_the_data() -> None:
    redactor = CassetteRedactor([KEY])
    data = {
        "message": f"invalid key {KEY}.",
        "nested": [{"inner": (f"a{KEY}b", 3)}],
        KEY: "as a key",
    }
    assert redactor.redact(data) == {
        "message": f"invalid key {MASK}.",
        "nested": [{"inner": [f"a{MASK}b", 3]}],
        MASK: "as a key",
    }


def test_other_kinds_of_value_pass_through_unchanged() -> None:
    redactor = CassetteRedactor([KEY])
    for value in (None, True, 7, 2.5):
        assert redactor.redact(value) is value


def test_the_longer_of_two_overlapping_secrets_is_masked_whole() -> None:
    redactor = CassetteRedactor(["abcdef", "abcdef-longer-secret"])
    assert redactor.redact("x abcdef-longer-secret y") == f"x {MASK} y"


def test_giving_the_same_secret_twice_changes_nothing() -> None:
    assert CassetteRedactor([KEY, KEY]).redact(f"a {KEY} b") == f"a {MASK} b"


def test_a_key_shaped_string_is_masked_even_when_it_was_not_named() -> None:
    assert CassetteRedactor().redact(f'{{"key": "{UNNAMED}"}}') == f'{{"key": "{MASK}"}}'
    assert CassetteRedactor().redact(f"key={UNNAMED}") == f"key={MASK}"


@pytest.mark.parametrize(
    "prose",
    [
        "task-management-workflows-for-teams",
        "risk-adjusted-return-calculations",
        "ask-me-anything-about-chapter-two",
        "sk-short-text",
    ],
)
def test_ordinary_prose_that_contains_sk_dash_is_left_alone(prose: str) -> None:
    redactor = CassetteRedactor()
    assert redactor.redact(prose) == prose
    assert not redactor.leaks(prose)


def test_a_key_shape_needs_sixteen_characters_after_the_prefix() -> None:
    assert CassetteRedactor().redact("sk-" + "a" * 15) == "sk-" + "a" * 15
    assert CassetteRedactor().redact("sk-" + "a" * 16) == MASK


def test_leaks_is_true_for_a_secret_anywhere_and_false_once_redacted() -> None:
    redactor = CassetteRedactor([KEY])
    for leaking in (
        f"x {KEY}",
        {"a": [f"{KEY}"]},
        {KEY: 1},
        (1, KEY),
        UNNAMED,
    ):
        assert redactor.leaks(leaking)
        assert not redactor.leaks(redactor.redact(leaking))


def test_leaks_is_false_for_clean_data_of_any_kind() -> None:
    redactor = CassetteRedactor([KEY])
    for clean in ("hello", {"a": [1, None, True, "b"]}, 3, None, {"n": float("nan")}):
        assert not redactor.leaks(clean)


@pytest.mark.parametrize("secret", ["", "   ", "abc", "abcde", " abcdef", "abcdef ", "abcde "])
def test_a_secret_too_short_or_padded_is_refused_so_an_unset_key_cannot_mask_prose(
    secret: str,
) -> None:
    with pytest.raises(ValueError, match="at least 6 characters"):
        CassetteRedactor([secret])


def test_a_secret_of_exactly_six_characters_is_accepted() -> None:
    assert CassetteRedactor(["abcdef"]).redact("xabcdefx") == f"x{MASK}x"
