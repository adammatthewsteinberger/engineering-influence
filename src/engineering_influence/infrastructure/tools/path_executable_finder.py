# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Finds an executable by name, the way a shell would."""

import os
import shutil

from engineering_influence.interfaces.executable_finder_interface import ExecutableFinderInterface


class PathExecutableFinder(ExecutableFinderInterface):
    """``shutil.which`` decides what counts: a name is looked up on ``PATH``, a path is checked as it is,
    and only an executable file that is not a directory is found.

    The answer is made absolute but a symbolic link is not followed, so the path stays the one the
    person named; the hasher follows the link when it reads the file.
    """

    def find(self, name: str) -> str | None:
        """The absolute path of the executable ``name`` refers to, or None when there is none."""
        found = shutil.which(name)
        return None if found is None else os.path.abspath(found)
