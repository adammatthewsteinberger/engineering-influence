# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How the ebook's internal cover is named and sized."""

from engineering_influence.models.epub.interfaces.cover_declaration_interface import (
    CoverDeclarationInterface,
)


class CoverDeclaration(CoverDeclarationInterface):
    """The Kindle Publishing Guidelines require an internal cover declared in the OPF."""

    NAME = "cover.jpg"
    ID = "cover-image"
    MIN_PX = (1600, 2500)  # KDP wants a large cover; verification fails a smaller one
