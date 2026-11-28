# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The home-directory directories a server's own interpreter and files live in."""

from pathlib import Path

from engineering_influence.infrastructure.tools.interfaces.sandbox_allowance_interface import (
    SandboxAllowanceInterface,
)


class SandboxAllowance(SandboxAllowanceInterface):
    """Every absolute path the server is started with names a file. The server needs that file's directory,
    the directory above it (a virtual environment's root), and the same two for the file the path really is
    (a virtual environment's interpreter often resolves into the installed Python, under the home directory).

    Only directories strictly below the home directory are returned. A path outside it adds nothing, and
    the home directory itself is never allowed, so no allowance can re-open the whole of it.
    """

    def paths(self, command: tuple[str, ...], home: Path) -> tuple[Path, ...]:
        found: set[Path] = set()
        real_home = home.resolve()
        for text in command:
            if not text.startswith("/"):
                continue
            named = Path(text)
            for start in (named, named.resolve()):
                for candidate in (start.parent, start.parent.parent):
                    for option in (candidate, candidate.resolve()):
                        if option != real_home and real_home in option.parents:
                            found.add(option)
        return tuple(sorted(found))
