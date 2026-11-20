# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The shape of a book slug."""

import re

from engineering_influence.models.typesetting.interfaces.book_slug_interface import (
    BookSlugInterface,
)


class BookSlug(BookSlugInterface):
    """A slug starts with a letter or digit, then holds letters, digits, hyphens and underscores.

    It names a book's config file, its build directory and its outputs, so it must never carry a
    path separator or a leading dash.
    """

    PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
