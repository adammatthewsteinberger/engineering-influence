# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Packages a book's finished files and listing into ``build/<slug>/release/kdp``, refusing a book that is not ready."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.interfaces.artifact_inventory_interface import ArtifactInventoryInterface
from engineering_influence.interfaces.publisher_interface import PublisherInterface
from engineering_influence.models.book_metadata import BookMetadata
from engineering_influence.models.kdp_bundle_file import KdpBundleFile
from engineering_influence.models.kdp_listing import KdpListing
from engineering_influence.models.publishing.path_relativizer import PathRelativizer
from engineering_influence.models.publishing.project_layout import ProjectLayout
from engineering_influence.models.typesetting.trim_size import TrimSize
from engineering_influence.services.interfaces.package_book_interface import PackageBookInterface
from engineering_influence.services.release.format_policy import FormatPolicy


class PackageBook(PackageBookInterface):
    """Only a book whose release check passes, with every required file present, is packaged.

    The files are the ones the artifact inventory names as required; their hashes are computed from the bytes
    copied, so the manifest describes exactly what is in the folder. The listing is built from the same limits the
    release check applies, so a listing that is written here cannot fail that check for its shape. Nothing is
    uploaded: KDP has no publishing API.
    """

    def __init__(
        self,
        layout: ProjectLayout,
        inventory: ArtifactInventoryInterface,
        publisher: PublisherInterface,
    ) -> None:
        self._layout = layout
        self._relativizer = PathRelativizer(layout.root)
        self._inventory = inventory
        self._publisher = publisher

    def package(self, slug: str, config: Mapping[str, Any], release_status: str) -> str:
        """Write the bundle and return a one-line summary; refuse a book that is not ready."""
        if release_status == "fail":
            raise BookBuildError(
                f"[{slug}] the release check fails; fix its errors before packaging (ei book audit {slug})"
            )
        metadata = self._metadata(slug, config)
        # The interior is a hardcover only when the book asks for one; the cover wrap follows the trim size.
        # The publication pipeline derives them the same way, so the bundle needs what the pipeline built.
        hardcover = bool(FormatPolicy().of(dict(config))["hardcover"])
        hardcover_wrap = TrimSize.for_name(config.get("trim_size")).hardcover
        artifacts = self._inventory.artifacts(
            slug, hardcover=hardcover, hardcover_wrap=hardcover_wrap
        )
        problems = self._inventory.problems(artifacts)
        if problems:
            raise BookBuildError("\n".join(f"[{slug}] {problem}" for problem in problems))
        files = tuple(self._file(item) for item in artifacts)
        listing = KdpListing(metadata).render(
            tuple((item.kind, item.name, item.size, item.sha256) for item in files)
        )
        manifest = json.dumps(
            {
                "slug": slug,
                "release_status": release_status,
                "files": [
                    {"kind": f.kind, "name": f.name, "bytes": f.size, "sha256": f.sha256}
                    for f in files
                ],
            },
            indent=2,
            sort_keys=True,
        )
        directory = self._layout.build / slug / "release" / "kdp"
        self._publisher.publish(
            directory, listing, manifest + "\n", {f.name: f.source for f in files}
        )
        return f"[{slug}] packaged {len(files)} files and the listing in {self._relativizer.relative(directory)}"

    def _metadata(self, slug: str, config: Mapping[str, Any]) -> BookMetadata:
        release = config.get("release")
        if not isinstance(release, dict):
            raise BookBuildError(f"[{slug}] the book has no [release] contract to list from")
        keywords, categories = release.get("keywords"), release.get("categories")
        if not isinstance(keywords, list) or not isinstance(categories, list):
            raise BookBuildError(f"[{slug}] release.keywords and release.categories are lists")
        try:
            return BookMetadata(
                title=str(config.get("title", "")),
                subtitle=str(config.get("subtitle", "")),
                description=str(config.get("description", "")),
                keywords=tuple(str(item) for item in keywords),
                categories=tuple(str(item) for item in categories),
            )
        except (ValueError, TypeError) as error:
            raise BookBuildError(f"[{slug}] the listing cannot be packaged: {error}") from error

    def _file(self, item: Mapping[str, Any]) -> KdpBundleFile:
        relative = str(item["path"])
        source = self._layout.root / relative
        return KdpBundleFile(
            kind=str(item["kind"]),
            name=Path(relative).name,
            source=source,
            size=int(item["bytes"]),
            sha256=str(item["sha256"]),
        )
