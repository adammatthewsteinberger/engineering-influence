"""The raster toolkit, built-in painter and style, painter registry, and plugin loading."""

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from engineering_influence.publishing.covers.box_blur import BoxBlur
from engineering_influence.publishing.covers.builtin_cover_style import BuiltinCoverStyle
from engineering_influence.publishing.covers.compositing import Compositing
from engineering_influence.publishing.covers.cover_painter import CoverPainter
from engineering_influence.publishing.covers.cover_plugin import CoverPlugin
from engineering_influence.publishing.covers.cover_plugin_loader import CoverPluginLoader
from engineering_influence.publishing.covers.film_grain import FilmGrain
from engineering_influence.publishing.covers.gradient_painter import GradientPainter
from engineering_influence.publishing.covers.ink import Ink
from engineering_influence.publishing.covers.layout_factory import LayoutFactory
from engineering_influence.publishing.covers.painter_registry import PainterRegistry
from engineering_influence.publishing.covers.quiet_zone import QuietZone
from engineering_influence.publishing.covers.soft_rect import SoftRect
from engineering_influence.publishing.covers.starfield import Starfield
from engineering_influence.publishing.covers.value_noise import ValueNoise
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError


def test_noise_is_seeded_bounded_and_shaped() -> None:
    a = ValueNoise().noise(40, 60, 4, np.random.default_rng(1))
    b = ValueNoise().noise(40, 60, 4, np.random.default_rng(1))
    assert a.shape == (40, 60) and a.min() >= 0 and a.max() <= 1 and np.array_equal(a, b)


def test_fbm_is_normalised_octaves() -> None:
    f = ValueNoise().fbm(32, 32, 2, 3, np.random.default_rng(2), gain=0.6)
    assert f.shape == (32, 32) and 0 <= f.min() and f.max() <= 1


def test_blur_leaves_tiny_sigmas_alone_and_smooths_the_rest() -> None:
    a = np.zeros((21, 21), np.float32)
    a[10, 10] = 1.0
    assert BoxBlur().apply(a, 0.4) is a
    blurred = BoxBlur().apply(a, 3)
    assert blurred.max() < 1.0 and blurred.sum() == pytest.approx(1.0, rel=1e-3)
    assert BoxBlur().apply(np.ones((5, 5, 3), np.float32), 1).shape == (5, 5, 3)


def test_compositing_helpers() -> None:
    comp = Compositing()
    x = np.array([0.0, 0.5, 1.0, 2.0], np.float32)
    assert comp.smoothstep(0, 1, x).tolist() == [0.0, 0.5, 1.0, 1.0]
    assert comp.mix(2.0, 4.0, 0.25) == 2.5
    assert comp.rgb(1, 0, 0.5).dtype == np.float32
    img = np.ones((2, 2, 3), np.float32)
    comp.over(img, np.array([[1, 0], [0, 0.5]], np.float32), (0, 0, 0), alpha=1.0)
    assert img[0, 0].tolist() == [0, 0, 0] and img[0, 1].tolist() == [1, 1, 1]
    assert img[1, 1].tolist() == [0.5, 0.5, 0.5]
    comp.add_light(img, np.ones((2, 2), np.float32), (0.1, 0.0, 0.0), gain=2.0)
    assert img[0, 1].tolist() == pytest.approx([1.2, 1.0, 1.0])


def test_soft_rect_is_feathered() -> None:
    m = SoftRect().mask(40, 40, (10, 10, 30, 30), 2)
    assert m[20, 20] == pytest.approx(1.0, abs=0.01) and m[0, 0] == 0
    assert 0 < m[10, 20] < 1
    assert SoftRect().mask(10, 10, (-5, -5, 3, 3), 0).sum() == 9


def test_starfield_adds_light_and_respects_weight() -> None:
    rng = np.random.default_rng(3)
    img = np.zeros((120, 120, 3), np.float32)
    Starfield().add(img, rng, 4000, 100)
    assert img.sum() > 0
    weighted = np.zeros((120, 120, 3), np.float32)
    Starfield().add(
        weighted, np.random.default_rng(3), 4000, 100, weight=np.zeros((120, 120), np.float32)
    )
    assert weighted.sum() == 0


def test_film_grain_is_zero_mean() -> None:
    img = np.zeros((50, 50, 3), np.float32)
    FilmGrain().add(img, np.random.default_rng(4), 0.1)
    assert abs(float(img.mean())) < 0.01 and img.max() <= 0.05


def test_ink_draws_lines_ellipses_and_polygons() -> None:
    ink = Ink(30, 30)
    ink.line([(2, 2), (28, 2)], 3)
    ink.ellipse(15, 15, 5, 5)
    ink.ellipse(15, 15, 10, 10, outline_px=1)
    ink.polygon([(2, 28), (10, 28), (6, 20)], value=128)
    mask = ink.mask()
    assert (
        mask.shape == (30, 30) and mask.max() == 1.0 and mask[15, 15] == 1.0 and mask[2, 15] > 0.5
    )
    assert 0 < mask[26, 6] < 1


def test_quiet_zone_covers_back_text_and_spine_only_on_print_layouts() -> None:
    factory = LayoutFactory()
    assert QuietZone().mask(factory.ebook(), 50, 40).sum() == 0
    layout = factory.paperback(249)
    w, h = layout.px
    zone = QuietZone().mask(layout, h, w)
    assert zone.shape == (h, w) and zone.max() > 0.9
    spine_x = round((layout.spine.x0 + layout.spine.x1) / 2 * layout.ppi)  # type: ignore[union-attr]
    assert zone[h // 2, spine_x] > 0.5 and zone[h // 2, w - 5] == 0


def test_gradient_painter_is_deterministic_and_obeys_extra_colours() -> None:
    layout = LayoutFactory().ebook()
    style = BuiltinCoverStyle().for_book({"title": "A Test Book"})
    a = GradientPainter().paint(layout, style)
    assert a.shape == (2560, 1600, 3) and a.dtype == np.float32
    assert np.array_equal(a, GradientPainter().paint(layout, style))
    style.extra.update(top=(1, 1, 1), bottom=(1, 1, 1))
    bright = GradientPainter().paint(layout, style)
    assert float(bright.mean()) > float(a.mean()) + 0.5


@pytest.mark.parametrize(
    ("title", "lines"),
    [
        ("Short", ["Short"]),
        ("Exactly Fourteen", ["Exactly", "Fourteen"]),
        ("The Case for Everything Whatsoever", ["The Case for", "Everything Whatsoever"]),
        ("Pneumonoultramicroscopic", ["Pneumonoultramicroscopic"]),
    ],
)
def test_builtin_style_splits_titles_near_the_middle(title: str, lines: list[str]) -> None:
    style = BuiltinCoverStyle().for_book({"title": title})
    assert style.title_lines == lines and style.painter == "gradient"
    assert style.seed == BuiltinCoverStyle().for_book({"title": title}).seed
    assert style.extra == {"subtitle_serif": True, "author_lift_in": 0.06}


class Flat(CoverPainter):
    def paint(self, layout: Any, style: Any) -> Any:
        return np.zeros((1, 1, 3), np.float32)


def test_registry_replaces_and_reports_unknown_painters() -> None:
    registry = PainterRegistry()
    with pytest.raises(BookBuildError, match=r"no cover painter named 'x' \(registered: none\)"):
        registry.get("x")
    first, second = Flat(), Flat()
    registry.register("flat", first)
    registry.register("flat", second)
    registry.register("a", first)
    assert registry.get("flat") is second
    with pytest.raises(BookBuildError, match=r"registered: a, flat"):
        registry.get("missing")


class DemoPlugin(CoverPlugin):
    def painters(self) -> dict[str, CoverPainter]:
        return {"demo": Flat()}

    def styles(self) -> dict[str, Any]:
        return {"demo-book": BuiltinCoverStyle().for_book({"title": "Demo"})}


class FakeEntry:
    def __init__(self, name: str, target: Any) -> None:
        self.name, self._target = name, target

    def load(self) -> Any:
        return self._target


def test_entry_point_plugins_are_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "engineering_influence.publishing.covers.cover_plugin_loader.entry_points",
        lambda group: [FakeEntry("demo", DemoPlugin)],
    )
    registry = PainterRegistry()
    styles = CoverPluginLoader().load(registry)
    assert list(styles) == ["demo-book"] and isinstance(registry.get("demo"), Flat)


def test_entry_point_that_is_not_a_plugin_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "engineering_influence.publishing.covers.cover_plugin_loader.entry_points",
        lambda group: [FakeEntry("bad", dict)],
    )
    with pytest.raises(BookBuildError, match="'bad' is not a CoverPlugin"):
        CoverPluginLoader().load(PainterRegistry())


def test_plugins_load_from_a_module_class_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "my_covers.py").write_text(
        "from tests_support import DemoPlugin\nThing = DemoPlugin\nNotPlugin = dict\n",
        encoding="utf-8",
    )
    (tmp_path / "tests_support.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setitem(sys.modules, "tests_support", sys.modules[__name__])
    registry = PainterRegistry()
    styles = CoverPluginLoader().load_reference("my_covers:Thing", registry)
    assert "demo-book" in styles and isinstance(registry.get("demo"), Flat)
    with pytest.raises(BookBuildError, match="is not a CoverPlugin"):
        CoverPluginLoader().load_reference("my_covers:NotPlugin", registry)
    for bad in ("nocolon", ":Class", "module:"):
        with pytest.raises(BookBuildError, match="must look like 'module:Class'"):
            CoverPluginLoader().load_reference(bad, registry)
    with pytest.raises(BookBuildError, match="cannot load cover plugin"):
        CoverPluginLoader().load_reference("no_such_module_xyz:Thing", registry)
    with pytest.raises(BookBuildError, match="cannot load cover plugin"):
        CoverPluginLoader().load_reference("my_covers:Missing", registry)
