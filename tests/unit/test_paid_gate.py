# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The ``paid`` marker: deselected by default, and locked a second time by the environment."""

import tomllib
from pathlib import Path
from typing import Any

import pytest
from paid_gate import PaidGate

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


class Item:
    """The two things the gate asks a test item."""

    def __init__(self, *marks: str) -> None:
        self.nodeid = "tests/paid/test_live.py::test_it"
        self._marks = set(marks)

    def get_closest_marker(self, name: str) -> object | None:
        return object() if name in self._marks else None


def start(environment: dict[str, str], *marks: str) -> None:
    item: Any = Item(*marks)
    PaidGate(environment).pytest_runtest_setup(item)


def test_an_unmarked_test_starts_whatever_the_environment_says() -> None:
    start({}, "toolchain")
    start({"EI_ALLOW_PAID": "1"})


def test_a_paid_test_starts_when_the_environment_allows_it() -> None:
    start({"EI_ALLOW_PAID": "1"}, "paid")


@pytest.mark.parametrize("value", [None, "", "0", "true", "yes", "1 ", "01"])
def test_a_paid_test_fails_unless_the_variable_is_exactly_1(value: str | None) -> None:
    environment = {} if value is None else {"EI_ALLOW_PAID": value}
    with pytest.raises(pytest.fail.Exception) as refused:
        start(environment, "paid")
    message = str(refused.value)
    assert "tests/paid/test_live.py::test_it" in message
    assert "EI_ALLOW_PAID=1" in message


def test_the_gate_is_registered_for_this_run(request: pytest.FixtureRequest) -> None:
    gate = request.config.pluginmanager.get_plugin("paid-gate")
    assert isinstance(gate, PaidGate)


def test_the_marker_is_declared_and_deselected_by_default() -> None:
    options = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["tool"]["pytest"]["ini_options"]
    assert "not paid" in options["addopts"]
    assert any(marker.startswith("paid:") for marker in options["markers"])
