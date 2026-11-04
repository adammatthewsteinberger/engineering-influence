"""Shared cover fixtures: the bundled fonts, a built-in style, and sample metadata."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from engineering_influence.publishing.covers.builtin_cover_style import BuiltinCoverStyle
from engineering_influence.publishing.covers.cover_style import CoverStyle
from engineering_influence.publishing.covers.font_loader import FontLoader
from engineering_influence.publishing.covers.gradient_painter import GradientPainter
from engineering_influence.publishing.covers.painter_registry import PainterRegistry
from engineering_influence.publishing.package_assets import PackageAssets

META: dict[str, Any] = {
    "title": "The Case for Testing",
    "subtitle": "A Short Subtitle That Wraps Over Two Lines",
    "author": "Ann Q. Author",
    "publisher": "Pub House",
    "website": "https://pub.example",
    "description": "First paragraph of the **back cover** blurb.\n\nSecond paragraph, longer and with more detail about the book.",
    "author_bio": "Ann writes about tests.\n\nA second bio paragraph that is ignored.",
}


@pytest.fixture(scope="session")
def fonts() -> Iterator[FontLoader]:
    with PackageAssets().directory() as assets:
        yield FontLoader([assets / "fonts"])


@pytest.fixture
def meta() -> dict[str, Any]:
    return dict(META)


@pytest.fixture
def style(meta: dict[str, Any]) -> CoverStyle:
    return BuiltinCoverStyle().for_book(meta)


@pytest.fixture
def registry() -> PainterRegistry:
    registry = PainterRegistry()
    registry.register("gradient", GradientPainter())
    return registry


@pytest.fixture
def font_path() -> Iterator[Path]:
    with PackageAssets().directory() as assets:
        yield assets / "fonts"
