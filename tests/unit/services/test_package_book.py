from collections.abc import Iterator
from contextlib import contextmanager

"""Packaging a book for KDP: only a passing release, with every file present, is written; the hashes match the bytes."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.publishing.directory_publisher import DirectoryPublisher
from engineering_influence.interfaces.artifact_inventory_interface import ArtifactInventoryInterface
from engineering_influence.interfaces.keep_awake_interface import KeepAwakeInterface
from engineering_influence.models.book_metadata import BookMetadata
from engineering_influence.models.kdp_bundle_file import KdpBundleFile
from engineering_influence.models.kdp_listing import KdpListing
from engineering_influence.models.publishing.project_layout import ProjectLayout
from engineering_influence.models.typesetting.trim_size import TrimSize
from engineering_influence.services.interfaces.package_book_interface import PackageBookInterface
from engineering_influence.services.package_book import PackageBook

DESCRIPTION = " ".join(["Windowsill herbs grow well when watered and turned each week."] * 9)
KEYWORDS = [f"keyword {n}" for n in range(7)]
CATEGORIES = ["Books > Crafts & Hobbies > Gardening", "Books > Cookbooks, Food & Wine"]


def config(**changes: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "title": "Windowsill Herbs",
        "subtitle": "A calm guide",
        "description": DESCRIPTION,
        "release": {"keywords": KEYWORDS, "categories": CATEGORIES},
    }
    values.update(changes)
    return values


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Inventory(ArtifactInventoryInterface):
    """Names the files a real release names, and says which are missing."""

    def __init__(self, layout: ProjectLayout, present: tuple[str, ...]) -> None:
        self._layout = layout
        self._present = present

    def artifacts(
        self, slug: str, *, hardcover: bool = False, hardcover_wrap: bool = True
    ) -> list[dict[str, Any]]:
        required = [f"output/{slug}.pdf", f"output/{slug}.epub"]
        items = []
        for path in required:
            real = self._layout.root / path
            exists = path in self._present and real.exists()
            item: dict[str, Any] = {"kind": "file", "path": path, "exists": exists}
            if exists:
                item["bytes"] = real.stat().st_size
                item["sha256"] = sha(real.read_bytes())
            items.append(item)
        return items

    def problems(self, artifacts: list[dict[str, Any]]) -> list[str]:
        return [f"missing artifact: {item['path']}" for item in artifacts if not item["exists"]]


@pytest.fixture
def project(tmp_path: Path) -> ProjectLayout:
    layout = ProjectLayout(tmp_path)
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "herbs.pdf").write_bytes(b"%PDF-1.7 interior")
    (tmp_path / "output" / "herbs.epub").write_bytes(b"PK epub")
    return layout


def packager(
    layout: ProjectLayout, present: tuple[str, ...] = ("output/herbs.pdf", "output/herbs.epub")
) -> PackageBook:
    return PackageBook(layout, Inventory(layout, present), DirectoryPublisher())


class NoAwake(KeepAwakeInterface):
    @contextmanager
    def hold(self) -> Iterator[None]:
        yield


def test_it_is_a_package_book_port() -> None:
    assert isinstance(packager(ProjectLayout(Path("/nonexistent"))), PackageBookInterface)


def test_a_passing_book_is_packaged_with_a_listing_a_manifest_and_copies(
    project: ProjectLayout,
) -> None:
    summary = packager(project).package("herbs", config(), "pass")
    kdp = project.build / "herbs" / "release" / "kdp"
    assert summary == "[herbs] packaged 2 files and the listing in build/herbs/release/kdp"
    assert (kdp / "herbs.pdf").read_bytes() == b"%PDF-1.7 interior"
    assert (kdp / "herbs.epub").read_bytes() == b"PK epub"
    manifest = json.loads((kdp / "MANIFEST.json").read_text())
    assert manifest["release_status"] == "pass"
    assert {f["name"]: f["sha256"] for f in manifest["files"]} == {
        "herbs.pdf": sha(b"%PDF-1.7 interior"),
        "herbs.epub": sha(b"PK epub"),
    }
    assert {f["name"]: f["bytes"] for f in manifest["files"]} == {"herbs.pdf": 17, "herbs.epub": 7}


def test_the_listing_is_the_text_to_paste_and_names_each_file(project: ProjectLayout) -> None:
    packager(project).package("herbs", config(), "warning")
    listing = (project.build / "herbs" / "release" / "kdp" / "listing.md").read_text()
    assert listing.startswith("# Windowsill Herbs\n\nSubtitle: A calm guide\n")
    assert "- keyword 0\n" in listing and "- keyword 6\n" in listing
    assert "- Books > Cookbooks, Food & Wine" in listing
    assert "| herbs.pdf |" in listing and sha(b"%PDF-1.7 interior") in listing
    assert "KDP has no publishing API" in listing


def test_a_failing_release_check_is_refused_and_nothing_is_written(project: ProjectLayout) -> None:
    with pytest.raises(
        BookBuildError, match=r"\[herbs\] the release check fails; fix its errors before packaging"
    ):
        packager(project).package("herbs", config(), "fail")
    assert not (project.build / "herbs").exists()


def test_a_missing_required_file_is_refused_and_nothing_is_written(project: ProjectLayout) -> None:
    (project.root / "output" / "herbs.epub").unlink()
    with pytest.raises(BookBuildError, match="missing artifact: output/herbs.epub"):
        packager(project, present=("output/herbs.pdf",)).package("herbs", config(), "pass")
    assert not (project.build / "herbs").exists()


def test_a_book_with_no_release_contract_is_refused(project: ProjectLayout) -> None:
    with pytest.raises(BookBuildError, match="has no \\[release\\] contract"):
        packager(project).package("herbs", {"title": "x"}, "pass")


def test_keywords_and_categories_must_be_lists(project: ProjectLayout) -> None:
    bad = config(release={"keywords": "seven", "categories": CATEGORIES})
    with pytest.raises(BookBuildError, match="are lists"):
        packager(project).package("herbs", bad, "pass")


def test_a_listing_outside_the_release_limits_is_refused_with_the_reason(
    project: ProjectLayout,
) -> None:
    bad = config(release={"keywords": KEYWORDS[:6], "categories": CATEGORIES})
    with pytest.raises(
        BookBuildError, match="the listing cannot be packaged: a listing has exactly 7 keywords"
    ):
        packager(project).package("herbs", bad, "pass")


def flags_for(project: ProjectLayout, values: dict[str, Any]) -> tuple[bool, bool]:
    """The (interior, wrap) hardcover flags the inventory was asked about for a book."""
    seen: list[tuple[bool, bool]] = []

    class Recording(Inventory):
        def artifacts(
            self, slug: str, *, hardcover: bool = False, hardcover_wrap: bool = True
        ) -> list[dict[str, Any]]:
            seen.append((hardcover, hardcover_wrap))
            return super().artifacts(slug, hardcover=hardcover, hardcover_wrap=hardcover_wrap)

    PackageBook(
        project, Recording(project, ("output/herbs.pdf", "output/herbs.epub")), DirectoryPublisher()
    ).package("herbs", values, "pass")
    [flags] = seen
    return flags


def test_a_book_that_does_not_ask_for_a_hardcover_is_not_asked_for_a_hardcover_interior(
    project: ProjectLayout,
) -> None:
    # A 6x9 trim can be printed as a hardcover, so its cover wrap is built; the interior is not, unless asked for.
    assert flags_for(project, config(trim_size="6x9")) == (False, True)


def test_a_book_that_asks_for_a_hardcover_is_asked_for_the_interior_and_the_wrap(
    project: ProjectLayout,
) -> None:
    assert flags_for(project, config(trim_size="6x9", formats={"hardcover": True})) == (True, True)


def test_a_trim_that_is_not_printed_as_a_hardcover_has_no_hardcover_wrap(
    project: ProjectLayout,
) -> None:
    trim = next(name for name in TrimSize.names() if not TrimSize.for_name(name).hardcover)
    assert flags_for(project, config(trim_size=trim)) == (False, False)


def test_the_bundle_file_is_named_by_a_plain_filename_and_has_a_real_hash() -> None:
    with pytest.raises(ValueError, match="plain filename"):
        KdpBundleFile("epub", "a/b.epub", Path("x"), 1, "0" * 64)
    with pytest.raises(ValueError, match="SHA-256"):
        KdpBundleFile("epub", "herbs.epub", Path("x"), 1, "short")
    with pytest.raises(ValueError, match="size"):
        KdpBundleFile("epub", "herbs.epub", Path("x"), -1, "0" * 64)


def test_the_listing_renders_its_metadata_and_its_files() -> None:
    metadata = BookMetadata(
        title="T",
        subtitle="S",
        description=DESCRIPTION,
        keywords=tuple(KEYWORDS),
        categories=tuple(CATEGORIES),
    )
    text = KdpListing(metadata).render((("epub", "herbs.epub", 7, "a" * 64),))
    assert "| epub | herbs.epub | 7 | " + "a" * 64 + " |" in text
    assert text.endswith("\n")


def test_the_publisher_refuses_a_symbolic_link_and_a_bad_name(tmp_path: Path) -> None:
    real = tmp_path / "real.pdf"
    real.write_bytes(b"x")
    link = tmp_path / "link.pdf"
    link.symlink_to(real)
    publisher = DirectoryPublisher()
    with pytest.raises(BookBuildError, match="is a symbolic link"):
        publisher.publish(tmp_path / "out", "L", "M", {"link.pdf": link})
    for name in ("a/b.pdf", "..", "listing.md", "MANIFEST.json", ""):
        with pytest.raises(BookBuildError, match="cannot be named"):
            publisher.publish(tmp_path / "out", "L", "M", {name: real})
    assert not (tmp_path / "out").exists() or not any((tmp_path / "out").iterdir())


def test_the_publisher_overwrites_its_own_files_and_leaves_others_alone(tmp_path: Path) -> None:
    folder = tmp_path / "kdp"
    folder.mkdir()
    (folder / "notes.txt").write_text("mine")
    source = tmp_path / "herbs.pdf"
    source.write_bytes(b"v1")
    DirectoryPublisher().publish(folder, "L1", "M1", {"herbs.pdf": source})
    source.write_bytes(b"v2")
    DirectoryPublisher().publish(folder, "L2", "M2", {"herbs.pdf": source})
    assert (folder / "listing.md").read_text() == "L2"
    assert (folder / "MANIFEST.json").read_text() == "M2"
    assert (folder / "herbs.pdf").read_bytes() == b"v2"
    assert (folder / "notes.txt").read_text() == "mine"


def test_the_manifest_says_the_status_it_was_packaged_with(project: ProjectLayout) -> None:
    packager(project).package("herbs", config(), "warning")
    manifest = json.loads(
        (project.build / "herbs" / "release" / "kdp" / "MANIFEST.json").read_text()
    )
    assert manifest["release_status"] == "warning"


@pytest.mark.parametrize("field", ["title", "subtitle", "description"])
def test_a_listing_missing_a_text_field_is_refused_not_defaulted(
    project: ProjectLayout, field: str
) -> None:
    without = {key: value for key, value in config().items() if key != field}
    with pytest.raises(
        BookBuildError, match=f"the listing cannot be packaged: the {field} is empty"
    ):
        packager(project).package("herbs", without, "pass")
    assert not (project.build / "herbs").exists()


def test_a_bundle_file_name_may_not_hold_a_backslash() -> None:
    with pytest.raises(ValueError, match="plain filename"):
        KdpBundleFile("epub", "a\\b.epub", Path("x"), 1, "0" * 64)


def test_a_build_folder_outside_the_project_is_named_by_its_full_path(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / "output").mkdir(parents=True)
    (project_root / "output" / "herbs.pdf").write_bytes(b"%PDF")
    (project_root / "output" / "herbs.epub").write_bytes(b"PK")
    elsewhere = tmp_path / "elsewhere"
    layout = ProjectLayout(project_root, build_dir=str(elsewhere))
    summary = packager(layout).package("herbs", config(), "pass")
    kdp = elsewhere / "herbs" / "release" / "kdp"
    assert summary == f"[herbs] packaged 2 files and the listing in {kdp}"
    assert (kdp / "listing.md").is_file()


def test_the_cli_prints_the_package_summary_it_is_given(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from engineering_influence.interactions.cli.book_cli import BookCli

    class Stub:
        def package(self, slug: str) -> str:
            return f"[{slug}] packaged 2 files and the listing in build/{slug}/release/kdp"

    argv = argparse.Namespace(book_command="package", root=tmp_path, slugs=["herbs"])
    assert BookCli(lambda root: Stub(), lambda state, settings: None, NoAwake()).run(argv) == 0
    assert (
        capsys.readouterr().out
        == "[herbs] packaged 2 files and the listing in build/herbs/release/kdp\n"
    )
