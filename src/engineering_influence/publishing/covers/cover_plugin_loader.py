# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Finds cover plugins: through entry points, or by an explicit `module:Class` reference."""

import importlib
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from engineering_influence.publishing.covers.cover_plugin import CoverPlugin
from engineering_influence.publishing.covers.cover_style import CoverStyle
from engineering_influence.publishing.covers.painter_registry import PainterRegistry
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError


class CoverPluginLoader:
    """A plugin class supplies painters and per-book styles; both are merged into the engine.

    Entry points suit an installed package (group `engineering_influence.covers`). A project that
    is a folder of scripts names its plugin in its configuration as `module:Class`.
    """

    GROUP = "engineering_influence.covers"

    def load(self, registry: PainterRegistry, root: Path | None = None) -> dict[str, CoverStyle]:
        """Register every entry-point plugin's painters; return the merged styles by slug."""
        styles: dict[str, CoverStyle] = {}
        for entry in entry_points(group=self.GROUP):
            styles.update(self._register(entry.load()(root=root), entry.name, registry))
        return styles

    def load_reference(
        self, reference: str, registry: PainterRegistry, root: Path | None = None
    ) -> dict[str, CoverStyle]:
        """Load one plugin from `module:Class`."""
        module_name, _, attribute = reference.partition(":")
        if not module_name or not attribute:
            raise BookBuildError(
                f"cover plugin reference {reference!r} must look like 'module:Class'"
            )
        try:
            plugin_class = getattr(importlib.import_module(module_name), attribute)
        except (ImportError, AttributeError) as error:
            raise BookBuildError(f"cannot load cover plugin {reference!r}: {error}") from error
        return self._register(plugin_class(root=root), reference, registry)

    def _register(self, plugin: Any, name: str, registry: PainterRegistry) -> dict[str, CoverStyle]:
        if not isinstance(plugin, CoverPlugin):
            raise BookBuildError(f"cover plugin {name!r} is not a CoverPlugin")
        for painter_name, painter in plugin.painters().items():
            registry.register(painter_name, painter)
        return plugin.styles()
