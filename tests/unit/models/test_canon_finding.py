# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""CanonFinding: a severity is ERROR or WARN, every part is named, and only an ERROR is an error."""

import pytest

from engineering_influence.models.canon_finding import CanonFinding


def test_only_error_and_warn_are_severities() -> None:
    with pytest.raises(ValueError, match="ERROR or WARN"):
        CanonFinding("INFO", "scene 1", "rule", "message")


def test_every_part_is_named() -> None:
    with pytest.raises(ValueError, match="has a where"):
        CanonFinding("ERROR", " ", "rule", "message")
    with pytest.raises(ValueError, match="has a rule"):
        CanonFinding("ERROR", "scene 1", "", "message")
    with pytest.raises(ValueError, match="has a message"):
        CanonFinding("ERROR", "scene 1", "rule", "  ")


def test_only_an_error_is_an_error() -> None:
    assert CanonFinding("ERROR", "scene 1", "rule", "message").is_error()
    assert not CanonFinding("WARN", "scene 1", "rule", "message").is_error()
