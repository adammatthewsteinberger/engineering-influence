# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Check, before a run starts, that this machine has what a book needs."""

from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.author_profile_loader_interface import (
    AuthorProfileLoaderInterface,
)
from engineering_influence.interfaces.executable_finder_interface import ExecutableFinderInterface
from engineering_influence.models.doctor_finding import DoctorFinding
from engineering_influence.services.interfaces.readiness_doctor_interface import (
    ReadinessDoctorInterface,
)


class ReadinessDoctor(ReadinessDoctorInterface):
    """Looks, and sends nothing: every finding comes from this machine's own files.

    A run that lacks an extra stops at once, but one that lacks a TeX tool writes every chapter first and fails
    at the last stage, ``build``. This check finds both before anything is written. Every failure says what to
    do about it. ``epubcheck`` is the one optional tool: only a strict release needs it, so it never fails the check. The model and the search are checked by their own doctors, because those do send something.
    """

    WHO = "install"
    EXTRAS: ClassVar[tuple[tuple[str, tuple[str, ...]], ...]] = (
        ("runtime", ("sqlmodel", "alembic", "httpx", "vibey_bootstrap")),
        ("publishing", ("markdown_it", "pypdf", "pdfplumber", "defusedxml")),
    )
    TOOLS: ClassVar[tuple[tuple[str, str], ...]] = (
        ("lualatex", "the interior PDF"),
        ("latexmk", "the interior PDF"),
        ("tex4ebook", "the EPUB"),
        ("zip", "the EPUB"),
    )
    RASTERISERS: ClassVar[tuple[str, ...]] = ("pdftoppm", "mutool")

    def __init__(
        self,
        installed: Callable[[str], bool],
        finder: ExecutableFinderInterface,
        loader: AuthorProfileLoaderInterface,
    ) -> None:
        self._installed = installed
        self._finder = finder
        self._loader = loader

    def check(self, profile: Path | None) -> tuple[DoctorFinding, ...]:
        """One finding for each extra, each tool and the author profile; nothing is sent anywhere."""
        return (
            *(self._extra(name, modules) for name, modules in self.EXTRAS),
            *(self._tool(name, purpose) for name, purpose in self.TOOLS),
            self._epubcheck(),
            self._rasteriser(),
            self._profile(profile),
        )

    def _extra(self, name: str, modules: tuple[str, ...]) -> DoctorFinding:
        missing = [module for module in modules if not self._installed(module)]
        if missing:
            return self._finding(
                f"extra {name}",
                False,
                f"missing {', '.join(missing)}: install engineering-influence with the [{name}] extra",
            )
        return self._finding(f"extra {name}", True, "installed")

    def _tool(self, name: str, purpose: str) -> DoctorFinding:
        found = self._finder.find(name)
        if found is None:
            return self._finding(
                f"tool {name}",
                False,
                f"not on PATH; the build stage needs it for {purpose} (docs/WORKER_IMAGE.md lists the packages)",
            )
        return self._finding(f"tool {name}", True, found)

    def _epubcheck(self) -> DoctorFinding:
        """Optional: a book builds without it, so its absence passes, and says what is lost."""
        found = self._finder.find("epubcheck")
        if found is None:
            return self._finding(
                "tool epubcheck (optional)",
                True,
                "not on PATH: the EPUB gets the built-in checks only, and a strict release will refuse to build",
            )
        return self._finding("tool epubcheck (optional)", True, found)

    def _rasteriser(self) -> DoctorFinding:
        for name in self.RASTERISERS:
            found = self._finder.find(name)
            if found is not None:
                return self._finding("tool page images", True, found)
        return self._finding(
            "tool page images",
            False,
            "neither pdftoppm (poppler) nor mutool is on PATH; the page check needs one of them",
        )

    def _profile(self, path: Path | None) -> DoctorFinding:
        if path is None:
            return self._finding(
                "author profile",
                False,
                "none named: set EI_AUTHOR_PROFILE or pass --author-profile FILE "
                "(examples/author-profile.example.toml is a starting point)",
            )
        try:
            profile = self._loader.load(path)
        except ApplicationError as error:
            return self._finding("author profile", False, error.message)
        if profile is None:
            return self._finding("author profile", False, f"there is no file at {path}")
        return self._finding("author profile", True, f"{path} reads as a profile")

    def _finding(self, check: str, passed: bool, detail: str) -> DoctorFinding:
        return DoctorFinding(self.WHO, check, passed, detail)
