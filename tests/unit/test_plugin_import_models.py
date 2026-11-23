# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""PluginFolder, PluginConversion and PluginImportResult hold what they are given and refuse nonsense."""

import pytest

from engineering_influence.models.interfaces.plugin_conversion_interface import (
    PluginConversionInterface,
)
from engineering_influence.models.interfaces.plugin_folder_interface import PluginFolderInterface
from engineering_influence.models.interfaces.plugin_import_result_interface import (
    PluginImportResultInterface,
)
from engineering_influence.models.plugin import Plugin
from engineering_influence.models.plugin_conversion import PluginConversion
from engineering_influence.models.plugin_folder import PluginFolder
from engineering_influence.models.plugin_import_result import PluginImportResult
from engineering_influence.models.skill import Skill

PLUGIN = Plugin("pack", 1, skills=(Skill("a", 1, (), sections=(("T", "text"),)),))


def folder(**changes: object) -> PluginFolder:
    values: dict[str, object] = {
        "name": "pack",
        "description": "",
        "servers": {"s": {"command": "/bin/x"}},
        "skills": (("a", "# text"),),
    }
    values.update(changes)
    return PluginFolder(**values)  # type: ignore[arg-type]


def test_a_folder_holds_its_parts() -> None:
    made = folder(set_aside=("hooks: x",))
    assert isinstance(made, PluginFolderInterface)
    assert made.name == "pack" and made.set_aside == ("hooks: x",)


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"name": " "}, ValueError),
        ({"name": 3}, ValueError),
        ({"description": 3}, TypeError),
        ({"servers": []}, TypeError),
        ({"servers": {3: {}}}, TypeError),
        ({"servers": {"s": "text"}}, TypeError),
        ({"skills": [("a", "b")]}, TypeError),
        ({"skills": (("a",),)}, TypeError),
        ({"skills": (("a", 3),)}, TypeError),
        ({"set_aside": ["x"]}, TypeError),
        ({"set_aside": (3,)}, TypeError),
    ],
)
def test_a_folder_that_is_not_shaped_right_is_refused(
    changes: dict[str, object], error: type[Exception]
) -> None:
    with pytest.raises(error):
        folder(**changes)


def test_a_conversion_holds_a_plugin_and_what_was_left_out() -> None:
    made = PluginConversion(PLUGIN, (("server x", "why"),), ("a note",), ("hooks: y",))
    assert isinstance(made, PluginConversionInterface)
    assert made.skipped == (("server x", "why"),) and made.notes == ("a note",)


@pytest.mark.parametrize(
    "changes",
    [
        {"plugin": "pack"},
        {"skipped": [("a", "b")]},
        {"notes": ["x"]},
        {"set_aside": ["x"]},
        {"skipped": (("only one",),)},
        {"skipped": ("ab",)},
    ],
)
def test_a_conversion_that_is_not_shaped_right_is_refused(changes: dict[str, object]) -> None:
    values: dict[str, object] = {"plugin": PLUGIN}
    values.update(changes)
    with pytest.raises(TypeError):
        PluginConversion(**values)  # type: ignore[arg-type]


def test_an_import_result_holds_a_conversion_and_a_path() -> None:
    made = PluginImportResult(PluginConversion(PLUGIN), "pack.toml")
    assert isinstance(made, PluginImportResultInterface)
    assert made.path == "pack.toml"


def test_an_import_result_needs_a_conversion_and_a_path() -> None:
    with pytest.raises(ValueError):
        PluginImportResult(PluginConversion(PLUGIN), " ")
    with pytest.raises(ValueError):
        PluginImportResult("not a conversion", "pack.toml")  # type: ignore[arg-type]
