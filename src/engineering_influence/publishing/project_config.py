# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A project's engineering-influence.toml: where things live and which cover plugin to load."""

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from engineering_influence.publishing.project_layout import ProjectLayout


@dataclass(frozen=True)
class ProjectConfig:
    """The consumer configuration of a book project.

    ``[books] config_dir`` and ``[artifacts] directory`` rename the books and output folders;
    ``[covers] plugin = "module:Class"`` names a cover plugin and ``[covers] fonts`` the folder
    holding its fonts. Every key is optional, so a project without the file still works.
    """

    root: Path
    books_dir: str = "books"
    output_dir: str = "output"
    build_dir: str = "build"
    cover_plugin: str | None = None
    cover_fonts: str = "covers/fonts"

    FILE_NAME = "engineering-influence.toml"

    @classmethod
    def load(cls, root: Path) -> "ProjectConfig":
        """Read root/engineering-influence.toml when it exists."""
        root = root.resolve()
        path = root / cls.FILE_NAME
        data = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        covers = data.get("covers", {})
        return cls(
            root=root,
            books_dir=str(data.get("books", {}).get("config_dir", "books")),
            output_dir=str(data.get("artifacts", {}).get("directory", "output")),
            build_dir=str(data.get("build", {}).get("directory", "build")),
            cover_plugin=covers.get("plugin"),
            cover_fonts=str(covers.get("fonts", "covers/fonts")),
        )

    def layout(self) -> ProjectLayout:
        """The directory layout this configuration describes."""
        return ProjectLayout(self.root, self.books_dir, self.output_dir, self.build_dir)

    def font_dirs(self) -> list[Path]:
        """Where the project keeps cover fonts."""
        return [self.root / self.cover_fonts]

    def activate(self) -> None:
        """Make the project importable, so a plugin named `module:Class` can be found."""
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))
