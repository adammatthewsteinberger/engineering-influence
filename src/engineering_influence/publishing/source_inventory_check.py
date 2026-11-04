# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every Markdown source is either printed or explicitly ignored."""

from pathlib import Path

from engineering_influence.publishing.issue_recorder import IssueRecorder


class SourceInventoryCheck:
    """Finds unlisted sources and ignore entries that name missing files."""

    def run(
        self,
        recorder: IssueRecorder,
        source: Path,
        listed: list[str],
        ignored: list[str],
    ) -> set[str]:
        """Record inventory issues and return the Markdown file names found."""
        found = {path.name for path in source.glob("*.md")}
        for name in sorted(found - (set(listed) | set(ignored))):
            recorder.record(
                "error",
                "unlisted-source",
                f"Markdown source is neither printed nor explicitly ignored: {name}",
                source / name,
            )
        for name in sorted(set(ignored) - found):
            recorder.record(
                "error",
                "missing-ignored-source",
                f"not_in_book names a missing file: {name}",
                source / name,
            )
        return found
