"""Reduces a finished fixture-book build to facts that do not change unless the code does."""

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from pypdf import PdfReader


class FixtureSnapshot:
    """A structural snapshot: no PDF bytes are kept, and no timestamps appear in it.

    Raw PDF bytes depend on the TeX Live release, so a PDF is reduced to its page count, page
    size and a hash of each page's text. An EPUB is repacked deterministically, so every member
    is hashed outright.
    """

    def of(self, root: Path, slug: str) -> dict[str, Any]:
        """The snapshot of one built book under ``root``."""
        output = root / "output"
        report_path = root / "build" / slug / "release" / "publication-report.json"
        return {
            "report": self._report(json.loads(report_path.read_text(encoding="utf-8"))),
            "pdf": self._pdf(output / f"{slug}.pdf"),
            "hardcover_pdf": self._optional_pdf(output / f"{slug}-hardcover.pdf"),
            "epub": self._epub(output / f"{slug}.epub"),
            "covers": sorted(
                path.name for path in (output / "covers" / slug).iterdir() if path.is_file()
            ),
        }

    def _report(self, report: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": report["status"],
            "steps": [[step["name"], step["status"]] for step in report["steps"]],
            "problems": report.get("problems", []),
            "findings": [
                [finding["severity"], finding["code"]]
                for finding in report["release_readiness"]["findings"]
            ],
        }

    def _optional_pdf(self, path: Path) -> dict[str, Any] | None:
        """A book with no hardcover (KDP offers none at 5x8) has no hardcover interior."""
        return self._pdf(path) if path.exists() else None

    def _pdf(self, path: Path) -> dict[str, Any]:
        reader = PdfReader(str(path))
        box = reader.pages[0].mediabox
        return {
            "pages": len(reader.pages),
            "size_pt": [round(float(box.width), 1), round(float(box.height), 1)],
            "page_text_sha256": [
                hashlib.sha256((page.extract_text() or "").encode("utf-8")).hexdigest()
                for page in reader.pages
            ],
        }

    def _epub(self, path: Path) -> dict[str, Any]:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            return {
                "mimetype_first_and_stored": infos[0].filename == "mimetype"
                and infos[0].compress_type == zipfile.ZIP_STORED,
                "members": {
                    info.filename: hashlib.sha256(archive.read(info)).hexdigest()
                    for info in sorted(infos, key=lambda info: info.filename)
                },
            }
