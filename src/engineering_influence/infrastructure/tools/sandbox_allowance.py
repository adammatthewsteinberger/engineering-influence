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
    the home directory itself is never allowed, so no allowance can re-open the whole of it. An allowance is
    refused when it is a credential directory, inside one, or an ancestor of one.
    """

    SECRET_DIRECTORIES = (".ssh", ".aws", ".gnupg", ".kube", ".config/gcloud", "Library/Keychains")

    def paths(self, command: tuple[str, ...], home: Path) -> tuple[Path, ...]:
        """The directories under home that the command names, resolved and sorted, with home itself and credential folders left out."""
        found: set[Path] = set()
        real_home = home.resolve()
        for text in command:
            if not text.startswith("/"):
                continue
            named = Path(text)
            for start in (named, named.resolve()):
                for candidate in (start.parent, start.parent.parent):
                    # Only the resolved directory is kept: binding a symlink would expose its target.
                    resolved = candidate.resolve()
                    if resolved == real_home or real_home not in resolved.parents:
                        continue
                    if not self._secret(resolved, real_home):
                        found.add(resolved)
        return tuple(sorted(found))

    def _secret(self, path: Path, home: Path) -> bool:
        """True when the resolved path is a credential directory, inside one, or an ancestor of one."""
        for name in self.SECRET_DIRECTORIES:
            plain = home / name
            for secret in {plain, plain.resolve()}:
                if path == secret or secret in path.parents or path in secret.parents:
                    return True
        return False
