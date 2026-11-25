# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The browse categories a book declares for its KDP listing."""

import re
from typing import Any

from engineering_influence.models.publishing.release_readiness_report import ReleaseReadinessReport
from engineering_influence.services.publishing.interfaces.category_check_interface import (
    CategoryCheckInterface,
)


class CategoryCheck(CategoryCheckInterface):
    """Up to three browse-tree paths, such as ``Books > Literature & Fiction > Mystery``.

    KDP lets a book sit in up to three categories chosen from Amazon's browse tree. That tree is
    not the BISAC subject-code list (``FIC009000``), which is a different scheme, so a BISAC code
    here is refused. The check cannot know Amazon's tree, which changes and has no API: it checks
    the count, the shape and the uniqueness, and the names are confirmed when the book is uploaded.
    A book that declares none gets a warning, so books written before this check keep passing.
    """

    LIMIT = 3
    BISAC = re.compile(r"^[A-Z]{3}\d{6}$")
    SEPARATOR = re.compile(r"\s*[>\u203a]\s*")

    def run(
        self, report: ReleaseReadinessReport, release: dict[str, Any], severity: str, ref: str
    ) -> None:
        """Add findings and record the categories."""
        declared = release.get("categories")
        if declared is None or declared == []:
            report.add(
                "warning",
                "categories-not-declared",
                "no browse categories declared; KDP takes up to three at upload",
                ref,
            )
            return
        if not isinstance(declared, list):
            report.add(severity, "categories-invalid", "release.categories must be a list", ref)
            return
        if len(declared) > self.LIMIT:
            report.add(
                severity,
                "too-many-categories",
                f"{len(declared)} categories declared; KDP allows up to {self.LIMIT}",
                ref,
            )
        seen: set[str] = set()
        for entry in declared:
            text = str(entry).strip()
            path = [part for part in self.SEPARATOR.split(text) if part]
            if self.BISAC.match(text):
                report.add(
                    severity,
                    "category-is-bisac",
                    f"{text!r} is a BISAC subject code; KDP categories are browse-tree paths",
                    ref,
                )
            elif not isinstance(entry, str) or len(path) < 2:
                report.add(
                    severity,
                    "category-not-a-path",
                    f"{entry!r} is not a browse path like 'Books > Literature & Fiction > Mystery'",
                    ref,
                )
            key = " > ".join(path).casefold()
            if key in seen:
                report.add(severity, "duplicate-category", f"{text!r} is declared twice", ref)
            seen.add(key)
        report.metadata["categories"] = [str(entry) for entry in declared]
