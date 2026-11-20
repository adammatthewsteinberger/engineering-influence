"""The public cover API: the façade's names, and plugins written against it."""

import importlib
from pathlib import Path
from typing import Any

import pytest

from engineering_influence import covers
from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.covers.cover_plugin_loader import CoverPluginLoader
from engineering_influence.infrastructure.covers.painter_registry import PainterRegistry


def test_the_facade_exports_exactly_the_documented_names() -> None:
    assert covers.__all__ == [
        "Box",
        "BoxBlur",
        "Compositing",
        "CoverBuilder",
        "CoverLayout",
        "CoverPainter",
        "CoverPlugin",
        "CoverPluginLoader",
        "CoverStyle",
        "FilmGrain",
        "Ink",
        "PainterRegistry",
        "ProjectLayout",
        "QuietZone",
        "SoftRect",
        "Starfield",
        "ValueNoise",
    ]
    assert all(isinstance(getattr(covers, name), type) for name in covers.__all__)


@pytest.mark.parametrize(
    "module",
    [
        "engineering_influence.publishing",
        "engineering_influence.publishing.project_layout",
        "engineering_influence.publishing.covers",
        "engineering_influence.publishing.covers.ink",
        "engineering_influence.publishing.covers.cover_plugin",
    ],
)
def test_the_old_publishing_package_is_gone(module: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module)


def test_a_plugin_written_against_the_facade_is_accepted_by_the_loader(tmp_path: Path) -> None:
    class Plugin(covers.CoverPlugin):
        def painters(self) -> dict[str, Any]:
            return {}

        def styles(self) -> dict[str, Any]:
            return {}

    class NotAPlugin:
        def __init__(self, root: Path | None = None) -> None:
            self.root = root

    assert Plugin(tmp_path).root == tmp_path
    registry = PainterRegistry()
    assert CoverPluginLoader()._register(Plugin(), "mine", registry) == {}
    with pytest.raises(BookBuildError, match="'bad' is not a CoverPlugin"):
        CoverPluginLoader()._register(NotAPlugin(), "bad", registry)
