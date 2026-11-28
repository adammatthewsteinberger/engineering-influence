# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Builds a book by laying its files out as a project in a scratch folder and running the whole pipeline on it."""

import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.audit.publication_findings import PublicationFindings
from engineering_influence.infrastructure.scratch_project import ScratchProject
from engineering_influence.interfaces.book_publisher_interface import BookPublisherInterface
from engineering_influence.interfaces.manuscript_builder_interface import (
    ManuscriptBuilderInterface,
)
from engineering_influence.models.manuscript_build import ManuscriptBuild


class TempProjectManuscriptBuilder(ManuscriptBuilderInterface):
    """Writes the files into a new temporary folder, publishes the book there, packages it, and reads the results back.

    The pipeline is the same one ``ei book publish`` runs: the audit gates, the interior PDF, the covers, the EPUB
    and the render check. A book that passes every gate is packaged into the KDP bundle, and the bundle's files
    are returned. The folder is private to the call and is removed when it ends, so nothing of the book is left on
    disk. Rendering every page can be switched off, for a rehearsal.

    A strict release also requires epubcheck to have run and the author's pricing inputs (a verification date and a
    source for the print cost) to be in the book config. A run cannot invent those, so a strict release is
    something the person asks for, and without it a missing price is a warning, not a failure.
    """

    TAIL = 500

    def __init__(
        self,
        publishers: Callable[[Path], BookPublisherInterface],
        no_render: bool = False,
        strict_release: bool = False,
    ) -> None:
        """Remember the publisher factory, and whether to skip rendering and to build a strict release."""
        self._publishers = publishers
        self._no_render = no_render
        self._strict_release = strict_release

    def build(self, files: Mapping[str, bytes], slug: str) -> ManuscriptBuild:
        """The build of the book."""
        with tempfile.TemporaryDirectory(prefix="ei-build-") as scratch:
            root = Path(scratch).resolve()
            ScratchProject.write(root, files)
            publisher = self._publishers(root)
            result, passed = publisher.publish(
                slug, no_render=self._no_render, strict_release=self._strict_release
            )
            errors = [*PublicationFindings.errors(result), *self._failures(result)]
            if passed:
                try:
                    publisher.package(slug)
                except BookBuildError as error:
                    passed = False
                    errors.append(str(error))
            if not passed and not errors:
                errors.append(f"the publication pipeline reported {result['status']!r}")
            release = root / "build" / slug / "release"
            reports = self._files(release)
            book = self._files(release / "kdp") if passed else ()
        steps = tuple((str(step["name"]), str(step["status"])) for step in result["steps"])
        return ManuscriptBuild(
            passed=passed,
            status="pass" if passed else "fail",
            errors=tuple(errors),
            warnings=PublicationFindings.warnings(result),
            steps=steps,
            reports=reports,
            book=book,
        )

    def _failures(self, result: dict[str, Any]) -> list[str]:
        found = [
            f"step {step['name']} failed: {str(step.get('stdout_tail', ''))[-self.TAIL :].strip()}"
            for step in result["steps"]
            if step["status"] == "fail"
        ]
        found += [str(problem) for problem in result.get("problems", [])]
        return found

    @staticmethod
    def _files(folder: Path) -> tuple[tuple[str, bytes], ...]:
        if not folder.is_dir():
            return ()
        return tuple(
            (path.name, path.read_bytes())
            for path in sorted(folder.iterdir())
            if path.is_file() and not path.name.startswith(".")
        )
