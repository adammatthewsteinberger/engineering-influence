# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose a cover builder, with the project's cover plugins loaded, on demand."""

from engineering_influence.infrastructure.covers.cover_builder import CoverBuilder
from engineering_influence.infrastructure.covers.cover_plugin_loader import CoverPluginLoader
from engineering_influence.infrastructure.covers.gradient_painter import GradientPainter
from engineering_influence.infrastructure.covers.painter_registry import PainterRegistry
from engineering_influence.interfaces.cover_builder_interface import CoverBuilderInterface
from engineering_influence.interfaces.cover_builder_provider_interface import (
    CoverBuilderProviderInterface,
)
from engineering_influence.models.covers.cover_style import CoverStyle
from engineering_influence.models.publishing.project_config import ProjectConfig


class CoverBuilderProvider(CoverBuilderProviderInterface):
    """Plugins can be slow to import and can fail, so they load only when covers are built."""

    def __init__(self, config: ProjectConfig) -> None:
        """Remember the project config the cover builder is set up for."""
        self._config = config

    def provide(self) -> CoverBuilderInterface:
        """Activate the project, load its cover plugins, and return a builder that uses them."""
        registry = PainterRegistry()
        registry.register("gradient", GradientPainter())
        loader = CoverPluginLoader()
        self._config.activate()
        styles: dict[str, CoverStyle] = loader.load(registry, self._config.root)
        if self._config.cover_plugin:
            styles.update(
                loader.load_reference(self._config.cover_plugin, registry, self._config.root)
            )
        return CoverBuilder(
            self._config.layout(),
            registry=registry,
            styles=styles,
            font_dirs=self._config.font_dirs(),
        )
