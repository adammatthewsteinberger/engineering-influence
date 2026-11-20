"""The public cover API: the façade's names, and the deprecated paths private projects still use."""

import importlib
import sys
from pathlib import Path
from typing import Any

import pytest

from engineering_influence import covers
from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.covers.cover_plugin_loader import CoverPluginLoader
from engineering_influence.infrastructure.covers.painter_registry import PainterRegistry

# The old module under engineering_influence.publishing.covers, and the name it exported.
DEPRECATED = {
    "box": "Box",
    "box_blur": "BoxBlur",
    "compositing": "Compositing",
    "cover_builder": "CoverBuilder",
    "cover_layout": "CoverLayout",
    "cover_painter": "CoverPainter",
    "cover_plugin": "CoverPlugin",
    "cover_plugin_loader": "CoverPluginLoader",
    "cover_style": "CoverStyle",
    "film_grain": "FilmGrain",
    "ink": "Ink",
    "painter_registry": "PainterRegistry",
    "quiet_zone": "QuietZone",
    "soft_rect": "SoftRect",
    "starfield": "Starfield",
    "value_noise": "ValueNoise",
}


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


@pytest.mark.parametrize(("stem", "name"), sorted(DEPRECATED.items()))
def test_each_old_path_still_works_warns_and_returns_the_same_class(stem: str, name: str) -> None:
    module_name = f"engineering_influence.publishing.covers.{stem}"
    sys.modules.pop(module_name, None)
    with pytest.warns(DeprecationWarning, match="engineering_influence.covers"):
        module = importlib.import_module(module_name)
    assert module.__all__ == [name]
    assert getattr(module, name) is getattr(covers, name)


def test_a_plugin_written_against_the_old_path_is_accepted_by_the_loader(tmp_path: Path) -> None:
    sys.modules.pop("engineering_influence.publishing.covers.cover_plugin", None)
    with pytest.warns(DeprecationWarning):
        old_plugin: Any = importlib.import_module(
            "engineering_influence.publishing.covers.cover_plugin"
        ).CoverPlugin

    class Plugin(old_plugin):  # type: ignore[misc]
        def painters(self) -> dict[str, Any]:
            return {}

        def styles(self) -> dict[str, Any]:
            return {}

    class NotAPlugin:
        def __init__(self, root: Path | None = None) -> None:
            self.root = root

    assert isinstance(Plugin(), covers.CoverPlugin)
    assert Plugin(tmp_path).root == tmp_path
    registry = PainterRegistry()
    assert CoverPluginLoader()._register(Plugin(), "mine", registry) == {}
    with pytest.raises(BookBuildError, match="'bad' is not a CoverPlugin"):
        CoverPluginLoader()._register(NotAPlugin(), "bad", registry)
